import unittest
import os
import json
import hashlib
import pywikibot

from bot import Bot
from corrector import process, get_chunks

TEST_PATH = os.path.dirname(os.path.realpath(__file__))
CACHE_FILES_PATH = os.path.join(TEST_PATH, '../cache')

class BotTestCase(unittest.TestCase):
    def setUp(self):
        self.test_bot = Bot('bot_corrector', 'dadess')
        self.pages = [['Metadecidim:_I_Jornades_i_Hackaton_del_desenvolupament_participatiu_del_Decidim.Barcelona_2016/11/25',
                       'Metadecidim: I Jornades i Hackaton del desenvolupament participatiu del Decidim.Barcelona',
                       'apunts'],
                      ['Mobile_Social_Congress_23-2-2016',
                       'MSC 2016 Mobile Social Congress',
                       'apunts']]

        for page in self.pages:
            note_page_title = os.path.join(page[0], page[2]).replace('_', ' ')
            h = hashlib.md5(note_page_title.encode('utf8'))
            outname = h.hexdigest()+'.txt'
            page.append(os.path.join(CACHE_FILES_PATH, outname))

    def tearDown(self):
        pass

    def test_get_page(self):
        for page in self.pages:
            self.test_bot.get_page(page[0])
            text = self.test_bot.page.text
            outpath = page[3]

            # get event name
            key = 'event'
            for template in self.test_bot.wikicode.filter_templates():
                for param in template.params:
                    if param.startswith(key):
                        event = param[len(key)+1:].strip()
                        break
            self.assertEqual(event, page[1])

            # get notes
            note_title = os.path.join(page[0], page[2])
            note_page = pywikibot.Page(self.test_bot.site,
                                       note_title)
            
            text_ref = note_page.text
            with open(outpath) as cache:
                text_cache = cache.read()
            self.assertEqual(text_ref, text_cache)

    def test_corrector_process(self):
        for page in self.pages:
            print(page[3])
            with open(page[3]) as cache:
                full_text = cache.read()
            response = process(page[1], full_text)
            self.assertIsNotNone(response.get('title'))
            self.assertIsNotNone(response.get('results'))

        #first_result = response.get('results')
        #self.assertIsNotNone(first_result.get('content'))
        #self.assertIsNotNone(first_result.get('language'))
        #self.assertIsNotNone(first_result.get('matches'))

    def test_get_chunks(self):
        for page in self.pages:
            with open(page[3]) as cache:
                full_text = cache.read()
            chunks = get_chunks(full_text)
            recovered_text = '\n'.join([chunk[0] for chunk in chunks])
            self.assertEqual(len(recovered_text), len(full_text))
            self.assertEqual(recovered_text, full_text)

    def test_correct_page(self):
        page = self.pages[0]
        self.test_bot.get_page(page[0])
        outpath = page[3]
        outjson = page[3].replace('.txt', '.json')

        # get note title
        note_title = os.path.join(page[0], page[2])

        # TODO get chunks/requests
        # TODO send chunks/requests

        # check corrections
        responses = self.test_bot.correct_note(note_title)

        with open(outjson, 'w') as out:
            json.dump(responses, out, indent = 2)
