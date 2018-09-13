__author__ = "Aditya Arjun, Richard Guo, An Nguyen, Elizabeth Zou"
__copyright__ = "Copyright 2018-present, Codeforces Companion (Coco)"

#Adapted from yjiao's application of the CF API (https://github.com/yjiao/codeforces-api)

# # Contest Parser v1
# Goal is to return the following table
#  
# handle | rating | contestID | problemID | success 
# --- | --- | --- | --- | --- | ---
# handle0 | 1234 | 633 | A | 1
# handle0 | 1234 | 633 | B | 1
# handle0 | 1234 | 633 | C | 0
#

import os
import re
import sys
import time
import requests
import pandas as pd
import re
from collections import defaultdict

def getProblemDataFromContest(contestID):
    url = 'http://codeforces.com/api/contest.standings?contestId=' + str(contestID) + '&from=1&count=1'
    r = requests.request('GET', url).json()['result']

    contest = r['contest']['name']
    startTimeSeconds = r['contest']['startTimeSeconds']

    problems = r['problems']
    probdf = pd.DataFrame.from_dict(problems)

    probdf['contestID'] = contestID
    probdf['contestName'] = contest
    probdf['startTimeSeconds'] = startTimeSeconds

    return probdf

def getSolveSuccessDF(contestID):

    urlbase = 'http://codeforces.com/api/'
    method = 'contest.standings'
    maxcnt = 100000
    # http://codeforces.com/api/contest.standings?contestId=566&from=1&count=5&showUnofficial=true
    url = urlbase + method + '?contestId=' + str(contestID) + '&from=1&count=' + str(maxcnt) + '&showUnofficial=false'
    r = requests.get(url).json()['result']
    rows = r['rows']
    problems = r['problems']
    contest = r['contest']

    # CHECK TO MAKE SURE THAT TEAMS ARE NOT ALLOWED!!!
    for r in rows:  # for each person
        if len(r['party']['members']) > 1:
            return None

    users = []
    points = []
    for r in rows:
        users.append(r['party']['members'][0]['handle'])

        userpts = [0] * len(problems)
        for i in range(len(problems)):
            userpts[i] = r['problemResults'][i]['points']
        points.append([1 if u > 0 else 0 for u in userpts])

    # Grab rating changes
    method = 'contest.ratingChanges'
    url = urlbase + method + '?contestId=' + str(contestID)
    ratingchanges = requests.get(url).json()['result']
    ratingdict = dict()
    for r in ratingchanges:
        ratingdict[r['handle']] = r['oldRating']

    # Create output df
    # start constructing dataframe
    array_out = []
    for i in range(len(users)):  # for each user in the contest
        hdl = users[i]
        rating = ratingdict[hdl]
        for j, p in enumerate(problems):  # for each problem in the contest, make a new row
            temp = dict.fromkeys(['handle', 'rating', 'contestID', 'problemID', 'success'])
            temp['handle'] = hdl
            temp['contestID'] = contestID
            temp['problemID'] = p['index']
            temp['success'] = points[i][j]
            temp['rating'] = rating
            array_out.append(temp)

    output = pd.DataFrame.from_dict(array_out)
    return output

def getContestList():
    url_contest = 'http://codeforces.com/api/contest.list?gym=false'
    r = requests.get(url_contest)  # there are some issues with Russian letters in contest names

    contests = r.json()['result']
    df_contests = pd.DataFrame.from_dict(contests)
    return list(df_contests.loc[df_contests.phase == 'FINISHED']['id'])

def isValidUser(handle):
    url = 'https://codeforces.com/api/user.info?handles=' + handle
    r = requests.get(url)

    info = r.json()

    return 'result' in info

def getUserSubmissions(handle):
    MAX_COUNT = 750
    url = 'https://codeforces.com/api/user.status?handle=' + handle + '&count=' + str(MAX_COUNT)
    r = requests.get(url)

    submissions = r.json()['result']

    dict_out = {}
    for row in submissions:
        ID = str(row['problem']['contestId']) + row['problem']['index']
        if not ID in dict_out:
            dict_out[ID] = []
            dict_out[ID].append(0)
            dict_out[ID].append(False)
            dict_out[ID].append(row['problem']['tags'])

        if row['verdict'] == 'OK':
            dict_out[ID][1] = True
        else:
            dict_out[ID][0] += 1

    out = []

    for k in dict_out.keys():
        ind = re.search('[A-Z]', k).start()

        row = dict.fromkeys(['contestID','problemID', 'tags','wrongSubs', 'solved'])
        row['contestID'] = k[0:ind]
        row['problemID'] = k[ind:]
        row['wrongSubs'] = dict_out[k][0]
        row['solved'] = int(dict_out[k][1])
        row['tags'] = dict_out[k][2]
        out.append(row)

    return pd.DataFrame.from_dict(out)