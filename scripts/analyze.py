from collections import Counter
import json
import os
import tabulate

def main():
    error_categories = {}
    for f in os.listdir('../cache/'):
        if f.endswith('.json'):
            res = json.load(open(os.path.join('../cache/',f)))
            for result in res['results']:
                language = result['response']['language']['code']
                if not error_categories.get(language):
                    error_categories[language] = []
                for match in result['response']['matches']:
                    error_categories[language].append(match['rule']['category']['id'])

    error_sets = {}
    for lang, lists in error_categories.items():
        error_sets[lang] = Counter(lists)

    for lang, counter in error_sets.items():
        print(lang)
        percentages = [(i, counter[i] / sum(counter.values())*100) for i, count in counter.most_common()]
        print(tabulate.tabulate(percentages))

    return error_sets

if __name__ == "__main__":
    main()
