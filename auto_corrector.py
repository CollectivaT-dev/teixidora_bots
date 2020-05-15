import logging

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
                                'EXIGEIX_VERBS_CENTRAL'],
                                      'en-US':
                               ['MORFOLOGIK_RULE_EN_US',
                                'UPPERCASE_SENTENCE_START',
                                'EN_SPECIFIC_CASE',
                                'EN_COMPOUNDS',
                                'EN_CONTRACTION_SPELLING']}
        # corpus initialized from outer scope
        self.corpus = set()

    def auto_correct(self, response):
        content = response['content']
        language = response['response']['language']['code']
        for match in response['response']['matches']:
            if match.get('replacements'):
                if len(match['replacements']) == 1:
                    i_start = match['offset']
                    i_end = match['offset']+match['length']
                    target = content[i_start:i_end]
                    replacement = match['replacements'][0]['value']
                    category = match['rule']['id']
                    if target.lower() not in self.corpus:
                       if replacement not in LT_MESSAGES and\
                          category in self.correction_categories[language]:
                        print(category, target, replacement)
                    else:
                        print('%s in corpus'%target)
        return response['content']
