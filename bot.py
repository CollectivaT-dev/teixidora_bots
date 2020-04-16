import sys
import re
import json
import time
import hashlib
import logging
import pywikibot

from pylanguagetool import api

LT_URL = 'https://languagetool.org/api/v2/'

def main(title):
    c_bot = Bot('corrector_bot')

    c_bot.get_page(title)
    c_bot.correct_notes()

class Bot(object):
    def __init__(self, botname, languagetool = LT_URL):
        # initializes the connection to teixidora semantic wiki
        self.site = pywikibot.Site('ca', 'teixidora')
        self.botname = botname
        self.languagetool = LT_URL

    def get_page(self, title):
        # get a new teixidora page initializing the rest of the variables
        self.title = title
        self.page = pywikibot.Page(self.site, title)

        self.notes = []
        self.corrected_notes = {}

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
        corrected_content = self.correct_content(content, language)

    def get_language(self, content):
        # placeholder
        return 'ca-ES'

    def correct_content(self, content, language):
        # TODO to be moved to LT processes class
        # Segments and sends the content to LT according to the
        # public api rate limits
        # http://wiki.languagetool.org/public-http-api
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
        # TODO smarted rate limit control needed
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

        h = hashlib.md5(self.title.encode('utf8'))
        outname = h.hexdigest()+'.json'
        with open('cache/'+outname, 'w') as out:
            json.dump(responses, out, indent = 2)

if __name__ == "__main__":
    title = sys.argv[1] 
    main(title)
