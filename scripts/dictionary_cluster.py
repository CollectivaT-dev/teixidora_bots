import json
import re
import unidecode
import numpy as np

from fuzzywuzzy import fuzz
from sklearn.cluster import DBSCAN

def main():
    # TODO get info directly from teixidora
    data = json.load(open('cache/global_corpora.json'))
    print('calculating organizations')
    org_groups = cluster(data['organizations'])
    print('calculating projects')
    pro_groups = cluster(data['projects'])
    print('calculating people')
    ppl_groups = cluster(data['people'])

    results = {'organizations': org_groups,
               'projects': pro_groups,
               'people': ppl_groups}

    with open('cache/cluster.json', 'w') as out:
        json.dump(results, out, indent=2)

def cluster(data):
    similarity_m = calculate_similarity(data)
    db = DBSCAN(eps=0.1, min_samples=1, metric='precomputed').fit(similarity_m)
    groups = {}
    for group in list(set(db.labels_)):
        groups[group] = []

    for group, name in zip(db.labels_, data):
        groups[group].append(name)
    return list(groups.values())

def calculate_similarity(data):
    mm = np.zeros(shape=(len(data),len(data)))
    for i, org1 in enumerate(data):
        for j, org2 in enumerate(data):
            mm[i][j] = distance(org1, org2)
    return mm

def distance(str1, str2):
    str1 = pre_filter(str1)
    str2 = pre_filter(str2)
    return 1-fuzz.token_set_ratio(str1, str2)/100.

def pre_filter(string):
    new = re.sub('·|\.$','',string)
    new = re.sub('l\.l', 'll', new)
    return unidecode.unidecode(new).lower()

if __name__ == "__main__":
    main()
