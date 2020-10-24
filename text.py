#import nltk
import ssl
import re
from nltk.corpus import stopwords
import string
import pandas as pd
import numpy as np

jobs = {'titles':None,'titles_filename':'position_titles.csv',
        'data':None,'filename':'jobopenings.csv'}

tags = None
match = None

score_key = {}

generic_titles = ['engineer','manager','developer','officer','designer','research','controller','supervisor',
                  'operator','consultant','scientist','analyst','machinist','advisor',
                  'programmer','architect','technician','postdoctor','artist','secretary','administrator',
                 'superintendent','coordinator','surveyor','representative','writer','graduate','counsellor',
                 'coach','advisory','teacher','partner','chef','secretarial',
                  'economist','planner','therapist']

modifiers = ['technical','site','development','technology','production','apac','administrative',
            'team','corporate','applications','application','system','excellence','integrity',
             'performance','management','strategy','big','enterprise','experience','company','corporation',
             'professional','group','solution','service','practice','success','creative','partnership',
             'commercial','greater','protocol','center','factor','deployment','force','sgunited',
             'strategic','department']

fields = ['qa','qc','civil','electrical','construction','structural','physical','business','building',
          'safety','piping','facilities','utility','trading','investment','commissioning','product',
          'hardware','mining','web','software','maintenance','firmware','python','customer','recruitment',
          'machine learning','deep learning','automation','robotics','human factors','hse','rotating',
          'project','schedule','planning','data','validation','verification','digital','optical','scrum',
          'computer science','failure analysis','fixed equipment','storage','network infrastructure','network architecture',
         'microcontroller','plant','cyber security','machine','sales','wireless','power','energy','sap','logistic',
         'microsoft dynamics','ui ux','ux ui','beauty','hyperion','actuarial','financial','amazon','marriage',
         'apple','google','workday','robotic','cybersecurity','agile','security','blast','health','environmental',
         'telecom','media','engagement','account','wealth','asset','analytics','client','reliability','java',
         'blockchain','intelligence','plc','geophysicist','renewable','carbon','footprint','farm','sustainability',
          'instrument','hairstyle','microbiologist','cloud','ecommerce','it security','academic','talent',
          'government','cyber','deltav','devops','agtech','innovation','mechanical','entrepreneur','fire',
          'finance', 'actuary','chemical','mobile app','quality assurance']

locations = ['asia pacific','singapore','english','japanese','chinese','southeast asia','asia',
             'global','region','regional','china','korea','indonesia','vietnam','myanmar','india',
            'japan','laos','thailand','asean','international']

ranks = ['senior','junior','sr','principal','lead','leader','fellow','associate','chief','vice president','president',
         'specialist','staff','mgrs','support','vp','executive','head','director','assistant','master','ceo',
         'assistant']

tagLists = {'generic':generic_titles, 'modifier': modifiers, 'field':fields, 'location':locations, 'rank':ranks}

#01 download stopwords

#def nltk_load():
#    try:
#        _create_unverified_https_context = ssl._create_unverified_context
#    except AttributeError:
#        pass
#    else:
#        ssl._create_default_https_context = _create_unverified_https_context

    #nltk.download('stopwords')

#02 title cleanup

def drop_paren(strValue,parentag='('):
    noparen = strValue
    retag = r''
    if parentag == '(':
        retag = r'\(([^\)]+)\)'
    elif parentag == '[':
        retag = r'\[(.*?)\]'
    parentk = re.search(retag,strValue)
    if not parentk is None:
        parentk = parentk[0]
        noparen = strValue.replace(parentk,'')
    return noparen

def cleanup(strValue):
    noparen = drop_paren(strValue,'(')
    noparen = drop_paren(noparen,'[')
    trimmed = noparen.strip()
    cleanStr = trimmed.lower()
    puncTags = list(string.punctuation)
    for tag in puncTags:
        cleanStr = cleanStr.replace(tag,'')
    return cleanStr

def load_jobs(df=None):
    global jobs
    if df is None:
        jobs['data'] = pd.read_csv(jobs['filename'])
    else:
        jobs['data'] = df

#load tags from dataframe
def load_tags(df):
    global tags, score_key, generic_titles, modifiers, fields, locations, ranks, tagLists
    tags = df.copy()
    for tt in tagLists:
        tagLists[tt] = tags[tags['tag_type'] == tt]['tag'].tolist()
        tag_scores = {}
        for tg in tagLists[tt]:
            scoreStr = tags[(tags['tag_type'] == tt) & (tags['tag'] == tg)]['score'].iloc[0]
            if scoreStr is not None:
                tag_scores[tg] = int(scoreStr)
            else:
                tag_scores[tg] = scoreStr
        score_key[tt] = tag_scores.copy()

    generic_titles = tagLists['generic']
    modifiers = tagLists['modifier']
    fields = tagLists['field']
    locations = tagLists['location']
    ranks = tagLists['rank']

def cleanup_job_titles():
    global jobs
    titledata = pd.DataFrame({'clean_title': jobs['data'].apply(
        lambda x: cleanup(x['position_title']), axis=1),
        'jobid':jobs['data']['jobid'],
        'posted_date':jobs['data']['posted_date'],
        'salaryHigh':jobs['data']['salaryHigh']})
    jobs['titles'] = titledata

#03 extract and classify tags from title

def extractTags(rawStr,tagList,tagsAsHash=True):
    extracted = [x.strip() for x in tagList if x in rawStr]
    residual = rawStr
    if len(extracted)>0:
        for tag in extracted:
            residual = residual.replace(tag,'')
    if tagsAsHash:
        hashStr = ':'.join(extracted)
        return residual, hashStr
    else:
        return residual, extracted

def extract_tags_from_title(titleStr):
    residual = titleStr
    tagHashes = []
    for tagList in [generic_titles, modifiers, fields, locations, ranks]:
        residual, tagHash = extractTags(residual,tagList)
        tagHashes.append(tagHash.strip())
    return residual, tagHashes

def classify_title(titleStr):
    residual, tagHashes = extract_tags_from_title(titleStr)
    generic = tagHashes[0]; modify = tagHashes[1]; field = tagHashes[2]
    location = tagHashes[3] ; rank = tagHashes[4]
    match_score = score_title(dict(zip(['generic','modifier','field','location','rank'],tagHashes)))
    return match_score, residual.strip(), generic, modify, field, location, rank

def score_title(tagHashes):
    'apply score from the list of tags using the score key'
    global score_key
    def hash_scores(tag_type,tagHash):
        tags = tagHash.split(':')
        tag_scores = [None if tg == '' else score_key[tag_type][tg] for tg in tags]
        return tag_scores

    scores = [s for tt in tagHashes for s in hash_scores(tt,tagHashes[tt])]
    match_score = None
    if -1 in scores:
        match_score = -1
    else:
        match_score = sum([0 if x is None else x for x in scores])

    return match_score

def extract_classify_titles():
    global jobs
    titledata = jobs['titles']
    titledata['match_auto'], \
    titledata['residual'], titledata['generic'], titledata['modifier'], \
        titledata['field'], titledata['location'], titledata['rank']= \
        zip(*titledata['clean_title'].map(classify_title))
    jobs['titles'] = titledata.copy()

def run_jobtitle_report():
    cleanup_job_titles()
    extract_classify_titles()
    jobs['titles'].to_csv(jobs['titles_filename'])
