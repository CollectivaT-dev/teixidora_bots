import re

from language_tool_python import LanguageTool
from langdetect import detect

# known teixidora languages written in langdetect format
# in order to be able skip erroneously detected languages
# TODO move to global config
# TODO should be the same as LANG_KEYS keys
TEIXIDORA_LANGS = ['en', 'ca', 'es', 'fr']

def process(title, full_text):
    response = {'title': title,
                'results': []}

    chunks = get_chunks(full_text)
    correct(chunks, response)
    return response

def get_chunks(full_text):
    chunks = []
    for paragraph in full_text.split('\n'):
        short = re.sub('[^\w ]+|\d+|_', '', paragraph)
        language = 'None'
        if len(short) > 25 and ' ' in paragraph:
            language = detect(paragraph)
        chunks.append((paragraph, language))
    return chunks

def correct(chunks, response):
    languages = get_languages(chunks)
    tools = {}
    for language in languages:
        if language in TEIXIDORA_LANGS:
            tools[language] = LanguageTool(language)

    results = []
    for i, chunk in enumerate(chunks):
        c_language = chunk[1]
        c_text = chunk[0]
        chunk_offset = sum([len(chunk[0]) for chunk in chunks[:i]])+i
        if c_language in TEIXIDORA_LANGS:
            cd_results = []
            for c_result in tools[c_language].check(c_text):
                cd_result = c_result.__dict__
                cd_result['offsetInContent'] = chunk_offset+cd_result['offset']
                cd_result['language'] = c_language
                cd_results.append(cd_result)
            results += cd_results

    result = {}
    result['content'] = '\n'.join([chunk[0] for chunk in chunks])
    result['languages'] = list(tools.keys())
    result['response'] = {}
    result['response']['matches'] = results
    response['results'] = [result]
    return response

def get_languages(chunks):
    languages = set([chunk[1] for chunk in chunks])
    languages.remove('None')
    return languages
