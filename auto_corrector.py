import logging

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

    def auto_correct(self, response):
        content = response['content']
        language = response['response']['language']['code']
        for match in response['response']['matches']:
            if match.get('replacements'):
                if len(match['replacements']) == 1:
                    target = content[match['offset']:match['offset']+match['length']]
                    replacement = match['replacements'][0]['value'] 
                    category = match['rule']['id']
                    if category in self.correction_categories[language]:
                       print(category, target, replacement)
        return response['content']
