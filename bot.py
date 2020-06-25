import sys
import os
import re
import json
import time
import hashlib
import logging
import argparse
import pywikibot
import mwparserfromhell

from pywikibot import pagegenerators
from pylanguagetool import api
from auto_corrector import AutoCorrector
from corpora_utils import get_global_corpora, cache_filepath, clean_token

LT_URL = 'https://languagetool.org/api/v2/'
RE_LANGS = {'ca-ES': re.compile('^catal'),
            'es': re.compile('^(cast|esp|spa)'),
            'en-US': re.compile('^(eng|ing|ang)'),
            'fr': re.compile('^fr')}
HOSTS = ['teixidora', 'localhost', 'dadess']
STOP_TOKENS = set(['es', 'la', 'el', 'a', 'dona'])

def main(args):
    c_bot = Bot('bot_corrector', host=args.host)

    count = 0
    if args.page:
        c_bot.get_page(args.page)
        c_bot.correct_notes()
        c_bot.implement_corrections()
        c_bot.send_corrections()
    elif args.all:
        for page in page_generator(c_bot.site):
            c_bot.get_page(page)
            if c_bot.params["bot import"] == 'Fet':
                if c_bot.params["bot correction"] == None:
                    #c_bot.change_param_value('bot correction', 'Activar')
                    pass
                elif c_bot.params["bot correction"] == 'Activar':
                    msg = 'correcting %s with cache %s'%(c_bot.title,
                                                         c_bot.outname)
                    logging.info(msg)
                    c_bot.correct_notes()
                    c_bot.implement_corrections()
                    c_bot.send_corrections()
                    count =+ 1
                    if count > 5:
                        break

def page_generator(site):
    category = pywikibot.Category(site, 'Esdeveniments')
    return pagegenerators.CategorizedPageGenerator(category)

class Bot(object):
    def __init__(self, botname, host = 'teixidora', languagetool = LT_URL):
        # initializes the connection to teixidora semantic wiki
        if host not in HOSTS:
            msg = 'given host %s not in defined hosts: %s'%(host, str(HOSTS))
            logging.error(msg)
            raise ValueError(msg)
        self.site = pywikibot.Site('ca', host)
        self.botname = botname
        self.languagetool = LT_URL
        self.params = {"bot import": None, 
                       "bot correction": None,
                       "human review": None}
        self.outname = None
        self.declared_language = None
        self.local_corpus = set()
        self.get_global_corpus()
        self.auto_corrector = AutoCorrector()

    def get_global_corpus(self):
        # TODO better file path handling
        if not os.path.exists(cache_filepath):
            global_corpus_dict = get_global_corpora(self.site)
        else:
            global_corpus_dict = json.load(open(cache_filepath))

        tokens = []
        for key, name_list in global_corpus_dict.items():
            if key not in ['exists', 'stop_words']:
                for name in name_list:
                    tokens += [clean_token(n.lower()) for n in name.split()]
            elif key == 'stop_words':
                # stop words can be compound
                for name in name_list:
                    tokens += [name.lower()]
        # convert list to set eliminating the empty strings
        self.global_corpus = set([token for token in tokens if token])

    def get_page(self, title_or_page):
        # get a new teixidora page initializing the rest of the variables
        if type(title_or_page) == str:
            self.title = title_or_page
            self.page = pywikibot.Page(self.site, self.title)
        else:
            self.page = title_or_page
            self.title = self.page.title()

        if not self.page.text:
            msg = "%s does not exist or not reachable"%title_or_page
            logging.warning(msg)
            #raise ValueError(msg)
        self.wikicode = mwparserfromhell.parse(self.page.text)

        # get bot correction and human review parameters
        self.get_correction_status()

        # get cache out file hash
        # TODO push to a db and use hash as the key
        h = hashlib.md5(self.title.encode('utf8'))
        self.outname = h.hexdigest()+'.json'
        self.outpath = 'cache/'+self.outname # TODO better path management

        # clean the notes and corrected notes objects if they were full
        self.notes = []
        self.corrected_notes = {}

        # get declared language
        self.get_declared_language()

        # get mentioned elements from semantic fields
        self.get_local_corpus()
        corpus = self.local_corpus.union(self.global_corpus)
        self.auto_corrector.corpus = corpus.difference(STOP_TOKENS)

    def get_correction_status(self):
        # for each page the parameters should be "resetted"
        self.params = {"bot import": None,
                       "bot correction": None,
                       "human review": None}

        for template in self.wikicode.filter_templates():
            for param in template.params:
                for key in self.params.keys():
                    if param.startswith(key):
                        i = len(key)+1
                        self.params[key] = param[i:].strip()

    def get_declared_language(self):
        lan_param = 'language'
        language = None
        for template in self.wikicode.filter_templates():
            for param in template.params:
                if param.startswith(lan_param):
                    language = template.get(lan_param)[len(lan_param)+1:]\
                                       .lower()
                    break
        # convert language to language code due to non-standard language
        # naming convenion
        if language:
            for lan_code, re_lan in RE_LANGS.items():
                if re_lan.search(language):
                    self.declared_language = lan_code
            if not self.declared_language:
                msg = 'WARNING: unknown language in the wiki page of the event %s'\
                      ''%language
                logging.warning(msg)
        else:
            msg = 'WARNING: language not declared for the page %s'%self.title
            logging.warning(msg)

    def get_local_corpus(self):
        # tokens extracted here will be ignored in the correction
        # implementation
        fields = ['projects mentioned', 'keywords', 'organizer',
                  'organizations mentioned', 'speakers',
                  'keywords in English', 'individuals mentioned']
        for field in fields:
            for template in self.wikicode.filter_templates():
                for param in template.params:
                    if param.startswith('%s='%field):
                        # we are interested in tokens not concepts hence
                        # we first get rid of the commas and then split
                        f_elements = template.get(field)
                        if f_elements:
                            elements_str = f_elements[len(field)+1:]\
                                                    .replace(',','')
                            elements = set(elements_str.strip().lower().split())
                            self.local_corpus = self.local_corpus.union(elements)
                            break
        # remove symbols if they appear as tokens
        stop_signs = set(['-', '?', '!', '/', '\\', '"', "'"])
        self.local_corpus = self.local_corpus.difference(stop_signs)

    def correct_notes(self):
        self.get_note_titles()
        for note in self.notes:
            self.corrected_notes[note] = self.correct_note(note)

    def get_note_titles(self):
        # placeholder to extract the apunts links
        self.notes = ['/'.join([self.title, 'apunts', '01'])]

    def correct_note(self, note):
        note_page = pywikibot.Page(self.site, note)
        # TODO extract only the content?
        content = note_page.text
        language = self.get_language(content)
        # TODO send the content to be corrected according to the LT rules
        return self.correct_content(content, language)

    def get_language(self, content):
        # TODO send also to LT to check
        if self.declared_language:
            return self.declared_language
        else:
            return 'ca-ES'

    def correct_content(self, content, language):
        # TODO to be moved to LT processes class
        # Segments and sends the content to LT according to the
        # public api rate limits
        # http://wiki.languagetool.org/public-http-api

        if os.path.isfile(self.outpath):
            msg = 'title exists in cache: %s'%self.title
            print(self.outpath)
            print(msg)
            logging.info(msg)
            with open(self.outpath) as f:
                responses = json.load(f)
            return responses
        else:
            per_minute_size_limit = 60e3 #KB
            per_req_size_limit = 6e3 # KB
            per_minute_req_limit = 12 # per minute
            sentences = content.split('. ')
            requests = []
            test_chunks = []
            chunk = []
            for sentence in sentences:
                chunk.append(sentence)
                total_chunk = '. '.join(chunk)
                if sys.getsizeof(total_chunk) > per_req_size_limit:
                    requests.append(total_chunk)
                    test_chunks.append((chunk[0], chunk[-1]))
                    chunk = []
            if chunk:
                # add last chunk
                requests.append('. '.join(chunk))
                test_chunks.append((chunk[0], chunk[-1]))

            # send requests to api
            # TODO smarter rate limit control needed
            responses = {'title': self.title, 'results': []}
            total_requests = len(requests)
            for i, request in enumerate(requests):
                try:
                    response = api.check(request,
                                     api_url=self.languagetool,
                                     lang=language)
                # TODO check language, if confidence lower than 0.90 resend
                except Exception as e:
                    msg = "%s language error. Trying to detect the language."\
                          ""%language
                    logging.warning(msg)
                    print('error')
                    response = api.check(test_chunks[i][1],
                                     api_url=self.languagetool,
                                     lang=language)
                    language = response['language']['detectedLanguage']['code']
                    msg = "%s detected as new language"%language
                    logging.info(msg)
                    response = api.check(request,
                                     api_url=self.languagetool,
                                     lang=language)
               
                message = '%i/%i response sent'%(i+1, total_requests)
                print(message)
                logging.info(message)
                if i+1 != total_requests:
                    # wait at all except the last LT api call
                    time.sleep(4)
                responses['results'].append({'content': request,
                                               'response': response})
            with open(self.outpath, 'w') as out:
                json.dump(responses, out, indent = 2)
            return responses

    def implement_corrections(self):
        self.targets = []
        if self.corrected_notes:
            # implements the corrections and pushes the results in
            # self.corrected_notes[note]['results'][i]['corrected_content']
            for url, responses in self.corrected_notes.items():
                for result in responses['results']:
                    final_corrected_content =\
                                   self.auto_corrector.auto_correct(result)
                    result['corrected_content'] = final_corrected_content
                target = [url,
                       '. '.join([c['content'] for c in responses['results']]),
                       '. '.join([c['corrected_content']\
                                              for c in responses['results']])]
                self.targets.append(target)
                with open(self.outpath.replace('.json', '_c.json'), 'w') as out:
                    json.dump(responses, out, indent = 2)
        else:
            msg = 'no corrections found for %s'%self.title
            logging.warning(msg)

    def send_corrections(self):
        for url, content, corrected_content in self.targets:
            # TODO add labels for revised=False
            # TODO check if correction webpage exists
            correction_page = pywikibot.Page(self.site, url+'/correccions')
            correction_page.text = content
            correction_page.save('BOT - original content imported from %s'%url)
            correction_page.text = corrected_content
            correction_page.save('BOT - corrections implemented')
        self.change_param_value('bot correction', 'Feta')
        self.change_param_value('human review', 'Pendent')

    def change_param_value(self, param, new_value):
        old_value = self.params[param]
        if old_value:
            new_text = re.sub('%s=%s'%(param, old_value),
                              '%s=%s'%(param, new_value),
                              self.page.text)
        else:
            # assumes there is always bot import parameter
            if self.params["bot import"] == None:
                msg = "cannot tick checkbox bcs parameter is not in the"\
                      " template and the anchor parameter bot import"\
                      " also doesn't exist.\n%s"%self.title
                logging.error(msg)
                raise ValueError(msg)
            else:
                bi_val = self.params['bot import']
                new_text = re.sub('bot import=%s\n'%bi_val,
                                  'bot import=%s\n|%s=%s\n'%(bi_val,
                                                             param,
                                                             new_value),
                                  self.page.text)
                if self.page.text == new_text:
                    msg = "parameter not changed, cannot save a new version"\
                          "\n%s -> %s for %s"%(param, new_value, self.page.title)
                    print(msg)
                    logging.warning(msg)
        self.page.text = new_text
        self.page.save('BOT - %s parameter changed to %s'%(param, new_value))

if __name__ == "__main__":
    usage = "usage: %(prog)s [options]"
    parser = argparse.ArgumentParser(description="wiki corrector bot launcher",\
                                     usage=usage)
    parser.add_argument('-p', '--page', type=str,
                        help='page to be corrected')
    parser.add_argument('-o', '--host', type=str, default='teixidora',
                        help='host to connect')
    parser.add_argument('-a', '--all', action='store_true',
                        help='correct all the tagged pages')
    args = parser.parse_args()

    logging_level = logging.INFO
    log_file = 'corrector.log'
    logging.basicConfig(filename=log_file,
                        format="%(asctime)s-%(levelname)s: %(message)s",
                        level=logging_level,
                        filemode='a')

    if not (args.page or args.all):
        parser.print_usage()
        raise ValueError('Either single page or all parameter needs to be given')
    main(args)
