import re
import os
import logging
import json
from copy import deepcopy

LT_MESSAGES = ["(s'ha arribat al límit de suggeriments)",
               "(suggestion limit reached)",
               "(se ha alcanzado el límite de sugerencias)"]
LANG_KEYS = {'ca': 'ca-ES', 'en': 'en-US', 'es':'es', 'fr':'fr'}
RE_SPACES = re.compile('\s')
RE_NO = re.compile('^\d')
PATH = os.path.abspath(os.path.dirname(__file__))

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
                                'EN_CONTRACTION_SPELLING',
                                'DIACRITICS_TRADITIONAL'],
                                      'es':[]}
        self.correction_stop_categories = {'ca-ES':
                               ['WHITESPACE_RULE',
                                'PHRASE_REPETITION',
                                'EN_NO_INFINITIU_CAUSAL',
                                'DONA_COMPTE'],
                                           'en-US':
                               ['WHITESPACE_RULE'],
                                           'es':
                               ['WHITESPACE_RULE'],
                                           'fr':
                               ['WHITESPACE_RULE',
                                'PAD']}
        # whether the corrections done offline or via API
        self.offline = None
        # corpus initialized from outer scope
        self.corpus = set()
        # known translations
        with open(os.path.join(PATH,'db/manual_corrections.json')) as mc:
            self.manual_corrections = json.load(mc)

    def auto_correct(self, response, scope='full'):
        self.content = response['content']
        new_content = deepcopy(self.content)
        # detect response format: online vs offline
        if response['response'].get('language'):
            self.offline = False
            languages = [response['response']['language']['code']]
        else:
            self.offline = True
            # get language list and convert from langdetect to LanguageTool codes
            languages = [LANG_KEYS[lang] for lang in response['languages']]

        difference = 0
        # since rule ids are unique per language dict can be flattened
        correction_stop_categories_lang = \
                [value for ls in self.correction_stop_categories.values() \
                       for value in ls]
        # put language as key if not in dict
        for i_language in languages:
            if not self.correction_categories.get(i_language):
                self.correction_categories[i_language] = {}

        if self.offline == True:
            offset_key = 'offsetInContent'
            length_key = 'errorLength'
        else:
            offset_key = 'offset'
            length_key = 'length'

        for match in response['response']['matches']:
            replace = False
            if match.get('replacements'):
                i_start = match[offset_key]
                i_end = match[offset_key]+match[length_key]
                target = self.content[i_start:i_end]
                if self.offline == True:
                    language = LANG_KEYS[match['language']]
                    category = match['ruleId']
                    replacement = match['replacements'][0]
                else:
                    language = languages[0]
                    category = match['rule']['id']
                    replacement = match['replacements'][0]['value']

                if replacement in LT_MESSAGES or\
                   RE_NO.search(target) or\
                   target.startswith('|'):
                    # there is no replacement
                    # starts with number, skip
                    # or wikicode
                    pass
                else:
                    if target.lower() in self.corpus or\
                       target.isupper() or\
                       (target[0].isupper() and len(target.split())==1) or\
                       category in correction_stop_categories_lang:
                        logging.info('%s in corpus or entity or rejected'%target)
                    else:
                        if self.manual_corrections[language].get(target.lower()):
                            replacement =\
                              self.manual_corrections[language][target.lower()]
                            replace = True
                            info = ' '.join(['m', category, target, replacement])
                            logging.info(info)
                        elif len(match['replacements']) == 1:
                                replace = True
                                info = ' '.join([category, target, replacement])
                                logging.info(info)
                        elif len(match['replacements']) > 1:
                                replace = True
                                alt_replacement = self.get_replacement(target,
                                                            match['replacements'])
                                if alt_replacement:
                                    replacement = alt_replacement
                                info = ' '.join(['>', category,
                                                 target, replacement])
                                logging.info(info)
                    if replace:
                        new_content = new_content[:i_start+difference]+\
                                      replacement+\
                                      new_content[i_end+difference:]
                        difference += len(replacement)-len(target)
        return new_content

    def get_replacement(self, target, matches):
        if self.offline == True:
            replacements = matches
        else:
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
                # use the top replacement (i.e. return none)
                pass
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
