import re
import logging
from copy import deepcopy

LT_MESSAGES = ["(s'ha arribat al límit de suggeriments)"]
RE_SPACES = re.compile('\s')

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
                                'SINO_SI_NO',
                                'A_NIVELL',
                                'SON',
                                'DE_EL_S_APOSTROFEN',
                                'ELA_GEMINADA_2CHAR'],
                                      'en-US':
                               ['MORFOLOGIK_RULE_EN_US',
                                'UPPERCASE_SENTENCE_START',
                                'EN_SPECIFIC_CASE',
                                'EN_COMPOUNDS',
                                'EN_CONTRACTION_SPELLING'],
                                      'es':[]}
        self.correction_stop_categories = {'ca-ES':
                               ['WHITESPACE_RULE',
                                'PHRASE_REPETITION',
                                'EN_NO_INFINITIU_CAUSAL',
                                'DONA_COMPTE'],
                                           'en-US':
                               ['WHITESPACE_RULE'],
                                           'es':
                               ['WHITESPACE_RULE']}
        self.typo = ['MORFOLOGIK_RULE_CA_ES', 'MORFOLOGIK_RULE_EN_US']
        # corpus initialized from outer scope
        self.corpus = set()

    def auto_correct(self, response, scope='full'):
        self.content = response['content']
        new_content = deepcopy(self.content)
        language = response['response']['language']['code']
        difference = 0
        for match in response['response']['matches']:
            replace = False
            if match.get('replacements'):
                i_start = match['offset']
                i_end = match['offset']+match['length']
                target = self.content[i_start:i_end]
                replacement = match['replacements'][0]['value']
                category = match['rule']['id']
                if target.lower() not in self.corpus and\
                   replacement not in LT_MESSAGES and\
                   not target.isupper() and\
                   not target.startswith('|'):
                    if len(match['replacements']) == 1 and\
                       category in self.correction_categories[language]:
                            replace = True
                            info = ' '.join([category, target, replacement])
                            logging.info(info)
                    elif len(match['replacements']) > 1 and\
                         category in self.typo:
                            replace = True
                            alt_replacement = self.get_replacement(target,
                                                        match['replacements'])
                            if alt_replacement:
                                print('for %s:%s instead of %s'%(target,
                                                               alt_replacement,
                                                               replacement))
                                replacement = alt_replacement
                            info = ' '.join(['>', category,
                                             target, replacement])
                            logging.info(info)
                    else:
                        if scope == 'full' and\
                     category not in self.correction_stop_categories[language]:
                            replace = True
                            info = ' '.join(['-', category,
                                         target, replacement])
                            logging.info(info)
                    if replace:
                        new_content = new_content[:i_start+difference]+\
                                      replacement+\
                                      new_content[i_end+difference:]
                        difference += len(replacement)-len(target)
                else:
                    logging.info('%s in corpus'%target)
        return new_content

    def get_replacement(self, target, matches):
        replacements = [m['value'] for m in matches]
        replacement = None
        if re.search('\s%s\s'%replacements[0], self.content, re.IGNORECASE):
            top_in_corpus = True
        else:
            top_in_corpus = False
        replacement_in_corpus = False
        possible_replacements = []
        for possible_repl in replacements[1:]:
            if RE_SPACES.sub('', target) == RE_SPACES.sub('', possible_repl):
                replacement_in_corpus = True
                for token in possible_repl.split():
                    if not re.search('\s%s\s'%token, self.content, re.IGNORECASE):
                        replacement_in_corpus = False
                possible_replacements.append((possible_repl,
                                              replacement_in_corpus))
                if not top_in_corpus and replacement_in_corpus:
                    break
        if not top_in_corpus:
            if replacement_in_corpus:
                # if top repl unknown and there is one known replacement
                # use the in corpus replacement
                replacement = possible_repl
            else:
                # if top repl unknown and there is no known replacement
                # use the first possible replacement
                if possible_replacements:
                    replacement = possible_replacements[0][0]
        else:
            if replacement_in_corpus:
                # if top repl in corpus and there is one known replacement
                # use the in corpus replacement
                replacement = possible_repl
            else:
                # if top repl in corpus and there is no known replacement
                # use top replacement (i.e. return none)
                pass
        return replacement
