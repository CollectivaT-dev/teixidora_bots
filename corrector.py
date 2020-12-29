import re

from language_tool_python import LanguageTool
from langdetect import detect

def process(title, full_text):
    response = {'title': title,
                'results': []}

    chunks = get_chunks(full_text)
    return response

def get_chunks(full_text):
    chunks = []
    for paragraph in full_text.split('\n'):
        short = re.sub('[^\w ]+|\d+|_', '', paragraph)
        if len(short) > 25 and ' ' in paragraph:
            language = detect(paragraph)
    return chunks
