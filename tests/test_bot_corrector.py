import unittest
import os
import json
import hashlib
import pywikibot

from bot import Bot
from corrector import process, get_chunks, correct
from auto_corrector import AutoCorrector

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

        self.test_chunks = [("'''MOBILE SOCIAL CONGRESS'''", 'None'),
('', 'None'),
("'''17:45h''' Programari lliure i xarxa oberta, amb Aleix Pol de KDE eV i Laura Mora de Capa8 i Guifi.net", 'ca'),
('', 'None'),
("'''18:30h''' L’origen dels minerals amb què es fan els mòbils, amb Maria Cañadas (presidenta d'Amnistia Internacional Catalunya)", 'ca'),
("Parlarà d'un informe:", 'None'),
("","None"),
('DEMOCRATIC REPUBLIC OF CONGO: "THIS IS WHAT WE DIE FOR": HUMAN RIGHTS ABUSES IN THE DEMOCRATIC REPUBLIC OF THE CONGO POWER THE GLOBAL TRADE IN COBALT',"en"),
('El govern no ha volgut regular la mineria artesanal. La cadena de subministrament cal conèixer-la. MDL empresa xinesa de cobalt, un dels majors fabricants del món de productes de cobalt, es ven a fabricants de components...', 'ca'),
('Perspectiva desde el lab, lo "lab" y los sistemas de innovación. Una ínfima minoría de la población innova mientras que el resto cosume.', 'es')
                      ]

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

            # test get_notes
            self.test_bot.get_note_titles()
            self.assertEqual(self.test_bot.notes[0], note_title)

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

            with open(page[3].replace('.txt', '_nc.json'), 'w') as out:
                json.dump(response, out, indent = 2)

            results = response.get('results')
            first_result = results[0]
            self.assertIsNotNone(first_result.get('response'))
            self.assertIsNotNone(first_result.get('content'))
            self.assertIsNotNone(first_result.get('languages'))
            self.assertIsNotNone(first_result['response'].get('matches'))
            self.assertIsNotNone(first_result['response']['matches'][0]\
                                                              .get('language'))

            # check if offset arithmetic is correct
            content = first_result['content']
            for match in first_result['response']['matches'][-4:-1]:
                offset_in_context = match['offsetInContext']
                offset_absolute = match['offsetInContent']
                length = match['errorLength']
                ref_in_context =\
                   match['context'][offset_in_context:offset_in_context+length]
                ref_in_content =\
                   content[offset_absolute:offset_absolute+length]
                self.assertEqual(ref_in_context, ref_in_content) 

    def test_get_chunks(self):
        for page in self.pages:
            with open(page[3]) as cache:
                full_text = cache.read()
            chunks = get_chunks(full_text)
            recovered_text = '\n'.join([chunk[0] for chunk in chunks])
            self.assertEqual(len(recovered_text), len(full_text))
            self.assertEqual(recovered_text, full_text)

            with open(page[3].replace('.txt', '_chunks.txt'), 'w') as out:
                for chunk in chunks:
                    out.write('%s\t%s\n'%(chunk[1], chunk[0]))

    def test_correct(self):
        response = {'title':'test'}
        correct(self.test_chunks, response)
        self.assertNotEqual(len(response['results']), 0)

    def test_auto_corrector(self):
        auto_corrector = AutoCorrector()
        for page in self.pages:
            with open(page[3].replace('.txt','_nc.json')) as f:
                responses = json.load(f)
            for result in responses['results']:
                result['corrected_content'] =\
                                            auto_corrector.auto_correct(result)

            for c in responses['results']:
                self.assertIsNotNone(c.get('corrected_content'))

            '''
            with open(page[3].replace('.txt','_nc.json'), 'w') as out:
                json.dump(responses, out, indent=2)
            '''

    def test_corrector_online(self):
        '''
        Test of original corrector
        '''
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

        '''
        with open(outjson, 'w') as out:
            json.dump(responses, out, indent = 2)
        '''
