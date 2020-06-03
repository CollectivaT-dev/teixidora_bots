import json
import re

from pywikibot.data import api

# TODO better filepath handling
cache_filepath = 'cache/global_corpora.json'
query_reference = {'organizations':
                   {'query':'[[Has event organizations mentioned::+]]'\
                            'OR[[Has event organizer::+]]|mainlabel=-|'\
                            'headers=hide |increase=log|?'\
                            'Has event organizations mentioned|'\
                            '?Has event organizer|limit=10000',
                    'filter_fields':['Has event organizations mentioned',
                                     'Has event organizer']},
                    'people':
                     {'query':'[[Has event individuals mentioned::+]]'\
                              'OR[[Has event speaker::+]]|mainlabel=-|'\
                              'headers=hide|increase=log|?'\
                              'Has event individuals mentioned|?'\
                              'Has event speaker|limit=10000',
                      'filter_fields':['Has event individuals mentioned']},
                    'projects':
                     {'query':'[[Has event projects mentioned::+]]|'\
                              'mainlabel=-|headers=hide|increase=log|?'\
                              'Has event projects mentioned|limit=1000',
                      'filter_fields':['Has event projects mentioned']}}

def get_global_corpora(site):
    corpora = {}
    exists_dict = {}
    for corpus_name, corpus_info in query_reference.items():
        result_list = []
        results = get_results(site, corpus_info['query'])
        for event, result in results['query']['results'].items():
            for filter_field in corpus_info['filter_fields']:
                for mentioned in result['printouts'][filter_field]:
                    result_list.append(mentioned['fulltext'])
                    if mentioned['exists']:
                        exists_dict[mentioned['fulltext']] = mentioned['fullurl']
        corpora[corpus_name] = list(set(result_list))
        corpora['exists'] = exists_dict
        with open(cache_filepath, 'w') as out:
            json.dump(corpora, out, indent=2)
    return corpora

def get_results(site, query):
    q = api.Request(site=site, parameters={'action': 'ask', 'query': query})
    return q.submit()
    
def clean_token(token):
    return re.sub('[()-]','', token)
