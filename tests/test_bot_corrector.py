import unittest
import os
import json
import hashlib
import pywikibot

from bot import Bot
from corrector import process

TEST_PATH = os.path.dirname(os.path.realpath(__file__))
CACHE_FILES_PATH = os.path.join(TEST_PATH, '../cache')

class BotTestCase(unittest.TestCase):
    def setUp(self):
        self.test_bot = Bot('bot_corrector', 'dadess')
        self.pages = [('Metadecidim:_I_Jornades_i_Hackaton_del_desenvolupament_participatiu_del_Decidim.Barcelona_2016/11/25',
                       'Metadecidim: I Jornades i Hackaton del desenvolupament participatiu del Decidim.Barcelona',
                       'apunts',
                       'a2176037d906ce808dee0065a4238466.txt'),
                      ('Mobile_Social_Congress_23-2-2016',
                       'MSC 2016 Mobile Social Congress',
                       'apunts',
                       'c09679da28ccc741dfb5080bc9fa9a21.txt')]

    def tearDown(self):
        pass

    def test_get_page(self):
        for page in self.pages:
            self.test_bot.get_page(page[0])
            text = self.test_bot.page.text

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
            
            # get hash name
            # TODO from original function for consistency
            h = hashlib.md5(note_page.title().encode('utf8'))
            outname = h.hexdigest()+'.txt'
            outpath = os.path.join(CACHE_FILES_PATH, outname)
            self.assertEqual(page[3], outname)

            '''
            with open(self.outpath, 'w') as out:
                out.write(note_page.text)
            '''

            text_ref = note_page.text
            with open(outpath) as cache:
                text_cache = cache.read()
            self.assertEqual(text_ref, text_cache)

    def test_corrector_process(self):
        for page in self.pages:
            with open(os.path.join(CACHE_FILES_PATH, page[3])) as cache:
                full_text = cache.read()
        response = process(full_text)
        
