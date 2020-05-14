import sys
import os
import re
import json
import time
import hashlib
import logging
import pywikibot
import mwparserfromhell

from pylanguagetool import api
from auto_corrector import AutoCorrector

LT_URL = 'https://languagetool.org/api/v2/'
RE_LANGS = {'ca-ES': re.compile('^catal'),
            'es-ES': re.compile('^(cast|esp|spa)'),
            'en-US': re.compile('^(eng|ing|ang)'),
            'fr-FR': re.compile('^fr')}

def main(title):
    c_bot = Bot('corrector_bot')

    c_bot.get_page(title)
    c_bot.correct_notes()
    c_bot.implement_corrections()

class Bot(object):
    def __init__(self, botname, host = 'teixidora', languagetool = LT_URL):
        # initializes the connection to teixidora semantic wiki
        if host == 'teixidora':
            self.site = pywikibot.Site('ca', 'teixidora')
        else:
            self.site = pywikibot.Site('ca', 'localhost')
        self.botname = botname
        self.languagetool = LT_URL
        self.outname = None
        self.declared_language = None
        self.local_corpus = set()

        self.auto_corrector = AutoCorrector()

    def get_page(self, title):
        # get a new teixidora page initializing the rest of the variables
        self.title = title
        self.page = pywikibot.Page(self.site, title)
        self.wikicode = mwparserfromhell.parse(self.page.text)

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
        self.auto_corrector.corpus = self.local_corpus

    def get_declared_language(self):
        lan_param = 'language'
        for template in self.wikicode.filter_templates():
            for param in template.params:
                if param.startswith(lan_param):
                    language = template.get(lan_param)[len(lan_param)+1:]\
                                       .lower()
                    break
        # convert language to language code due to non-standard language
        # naming convention
        for lan_code, re_lan in RE_LANGS.items():
            if re_lan.search(language):
                self.declared_language = lan_code
        if not self.declared_language:
            msg = 'WARNING: unknown language in the wiki page of the event %s'\
                  ''%language
            print(msg)
            logging.warning(msg)

    def get_local_corpus(self):
        # tokens extracted here will be ignored in the correction
        # implementation
        fields = ['projects mentioned', 'keywords', 'organizer',
                  'organizations mentioned', 'speakers',
                  'keywords in English']
        for field in fields:
            for template in self.wikicode.filter_templates():
                for param in template.params:
                    if param.startswith(field):
                        # we are interested in tokens not concepts hence
                        # we first get rid of the commas and then split
                        elements_str = template.get(field)[len(field)+1:]\
                                               .replace(',','')
                        elements = set(elements_str.strip().lower().split())
                        self.local_corpus = self.local_corpus.union(elements)
                        break

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
            print(msg)
            logging.info(msg)
            with open(self.outpath) as f:
                responses = json.load(f)
            return responses
        else:
            per_minute_size_limit = 60e3 #KB
            per_req_size_limit = 10e3 # KB
            per_minute_req_limit = 12 # per minute
            sentences = content.split('. ')
            requests = []
            chunk = []
            for sentence in sentences:
                chunk.append(sentence)
                total_chunk = '. '.join(chunk)
                if sys.getsizeof(total_chunk) > per_req_size_limit:
                    requests.append(total_chunk)
                    chunk = []
            if chunk:
                # add last chunk
                requests.append('. '.join(chunk))

            # send requests to api
            # TODO smarter rate limit control needed
            responses = {'title': self.title, 'results': []}
            total_requests = len(requests)
            for i, request in enumerate(requests):
                response = api.check(request,
                                     api_url=self.languagetool,
                                     lang=language)
                # TODO check language, if confidence lower than 0.90 resend
               
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
        if self.corrected_notes:
            # implements the corrections and pushes the results in
            # self.corrected_notes[note]['results'][i]['corrected_content']
            for url, responses in self.corrected_notes.items():
                for result in responses['results']:
                    final_corrected_content =\
                                   self.auto_corrector.auto_correct(result)
                    result['corrected_content'] = final_corrected_content
                with open(self.outpath.replace('.json', '_c.json'), 'w') as out:
                    json.dump(responses, out, indent = 2)
        else:
            msg = 'no corrections found for %s'%self.title
            logging.warning(msg)

if __name__ == "__main__":
    title = sys.argv[1] 
    main(title)
