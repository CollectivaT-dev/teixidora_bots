import logging
from copy import deepcopy

LT_MESSAGES = ["(s'ha arribat al límit de suggeriments)"]

class AutoCorrector(object):
    def __init__(self):
        self.correction_categories = {'ca-ES':
                               ['MORFOLOGIK_RULE_CA_ES',
                                'AL_INFINITIU',
                                'CONFUSIONS_ACCENT',
                                'LA_NA_NOM_FEMENI',
                                'ESPAI_DESPRES_DE_PUNT',
                                'EXIGEIX_ACCENTUACIO_GENERAL',
                                'CANVI_PREPOSICIONS',
                                'ES',
                                'CA_SIMPLE_REPLACE_ANGLICIMS',
                                'EXIGEIX_VERBS_CENTRAL',
                                'LO_NEUTRE',
                                'CA_SIMPLE_REPLACE',
                                'UPPERCASE_SENTENCE_START',
                                'DIFERENT_A',
                                'RELATIUS',
                                'EXCLAMACIO_APOSTROF',
                                'SINO_SI_NO'],
                                      'en-US':
                               ['MORFOLOGIK_RULE_EN_US',
                                'UPPERCASE_SENTENCE_START',
                                'EN_SPECIFIC_CASE',
                                'EN_COMPOUNDS',
                                'EN_CONTRACTION_SPELLING']}
        self.typo = ['MORFOLOGIK_RULE_CA_ES', 'MORFOLOGIK_RULE_EN_US']
        # corpus initialized from outer scope
        self.corpus = set()

    def auto_correct(self, response):
        content = response['content']
        new_content = deepcopy(content)
        language = response['response']['language']['code']
        difference = 0
        for match in response['response']['matches']:
            replace = False
            if match.get('replacements'):
                i_start = match['offset']
                i_end = match['offset']+match['length']
                target = content[i_start:i_end]
                replacement = match['replacements'][0]['value']
                category = match['rule']['id']
                if target.lower() not in self.corpus and\
                   replacement not in LT_MESSAGES and\
                   not target.isupper() :
                    if len(match['replacements']) == 1 and\
                       category in self.correction_categories[language]:
                            replace = True
                            print(category, target, replacement)
                    elif len(match['replacements']) < 5 and\
                         category in self.typo:
                            replace = True
                            print('>',category, target, replacement)
                    if replace:
                        new_content = new_content[:i_start+difference]+\
                                      replacement+\
                                      new_content[i_end+difference:]
                        difference += len(replacement)-len(target)
                else:
                    print('%s in corpus'%target)
        return new_content
