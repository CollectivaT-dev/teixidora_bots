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
    org_groups, org_keys = cluster(data['organizations'])
    print('calculating projects')
    pro_groups, pro_keys = cluster(data['projects'])
    print('calculating people')
    ppl_groups, ppl_keys = cluster(data['people'])

    org_groups.sort()
    pro_groups.sort()
    ppl_groups.sort()

    results = {'organizations': org_groups,
               'projects': pro_groups,
               'people': ppl_groups}
    key_results = {'organizations': org_keys,
                   'projects': pro_keys,
                   'people': ppl_keys}

    with open('cache/cluster_lists.json', 'w') as out:
        json.dump(results, out, indent=2)
    with open('cache/cluster_keys.json', 'w') as out:
        json.dump(key_results, out, indent=2)

    new_org_groups, new_org_keys = auto_assign(org_groups)
    new_org_groups, new_org_keys = order_groups(new_org_groups, data['exists'])
    new_pro_groups, new_pro_keys = auto_assign(pro_groups)
    new_pro_groups, new_pro_keys = order_groups(new_pro_groups, data['exists'])
    new_ppl_groups, new_ppl_keys = order_groups(ppl_groups, data['exists'])

    new_org_groups.sort()
    new_pro_groups.sort()
    new_ppl_groups.sort()

    results = {'organizations': new_org_groups,
               'projects': new_pro_groups,
               'people': new_ppl_groups}
    key_results = {'organizations': new_org_keys,
                   'projects': new_pro_keys,
                   'people': new_ppl_keys}

    with open('cache/auto_cluster_lists.json', 'w') as out:
        json.dump(results, out, indent=2)
    with open('cache/auto_cluster_keys.json', 'w') as out:
        json.dump(key_results, out, indent=2)


def cluster(data):
    similarity_m = calculate_similarity(data)
    db = DBSCAN(eps=0.1, min_samples=1, metric='precomputed').fit(similarity_m)
    groups = {}
    keys = {}
    for group in list(set(db.labels_)):
        groups[group] = []

    for group, name in zip(db.labels_, data):
        groups[group].append(name)
        keys[name] = int(group)
    # TODO group id -1 (noise) treatment
    return list(groups.values()), keys

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

def auto_assign(groups):
    ref = 0
    count = 0
    new_groups = []
    new_keys = {}
    for group in groups:
        if len(group) > 1:
            chars = [len(re.sub('\(.+\)','',g).strip())\
                     for g in list(group)]
            ref += 1
            if max(chars) - min(chars) < 6:
                count += 1
                new_groups.append(group)
            else:
                # append each element separately
                # or group into subgroups of equal lengths
                subgroups = {}
                for element in group:
                    length = len(re.sub('\(.+\)','',element).strip())
                    if not subgroups.get(length):
                        subgroups[length] = []
                    subgroups[length].append(element)
                for elements in subgroups.values():
                    new_groups.append(elements)
                    if len(elements) > 1:
                        count += 1
        else:
            new_groups.append(group)

    for i, group in enumerate(new_groups):
        for name in group:
            new_keys[name] = i

    print('%i out of %i automatically assigned'%(count, ref))
    return new_groups, new_keys

def order_groups(groups, exists):
    new_groups = []
    new_keys = {}
    for group in groups:
        sub_group = []
        if len(group) > 1:
            for g in group:
                if exists.get(g):
                    sub_group.append(g)
            if len(sub_group) > 1:
                msg = 'WARNING: more than 2 names with links discovered %s'\
                      ''%str(sub_group)
                print(msg)
            new_groups.append(sub_group + \
                                      [p for p in group if p not in sub_group])
        else:
            new_groups.append(group)

    for i, group in enumerate(new_groups):
        for name in group:
            new_keys[name] = i
    return new_groups, new_keys

if __name__ == "__main__":
    main()
