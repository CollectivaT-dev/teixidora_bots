import unittest
import os
import json

from auto_corrector import AutoCorrector

TEST_PATH = os.path.dirname(os.path.realpath(__file__))
CACHE_FILES_PATH = os.path.join(TEST_PATH, '../cache')

class AutoCorrectorTestCase(unittest.TestCase):
    def setUp(self):
        self.test_correcton_files = {'ca-ES':
                            ['3422059e057636482a2230c3aa87dfeb.json',
                             '36b63320f3a0e3be9fb5db9f6977ff2d.json',
                             '4640bc501a5249d012cd8fa1db31bd77.json',
                             'ef4f48c7860cba1910edafe6c7dbd332.json'],
                                     'en-US':
                            ['3c0b0033e4ae2e8182451a22159badea.json',
                             '9e1b1202e55d4add7e376d451e3afa64.json']}
        self.test_corrector = AutoCorrector()

    def tearDown(self):
        pass

    def test_auto_correct(self):
        for lang, files in self.test_correcton_files.items():
            print('testing for', lang)
            test_file = os.path.join(CACHE_FILES_PATH, files[0])
            with open(test_file) as tf:
                for result in json.load(tf)['results']:
                    corrected_content = self.test_corrector.auto_correct(result)

                    # assert that the result is string that has a similar length
                    # to the input content
                    # format check
                    difference = abs(len(result['content'])-len(corrected_content))
                    self.assertLessEqual(difference/len(result['content']),0.1)

                    # do language checks
                    if lang == 'ca-ES':
                       pass 
                
