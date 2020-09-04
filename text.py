import nltk
import ssl
import re
from nltk.corpus import stopwords
import string
import pandas as pd
import numpy as np

jobs = {'titles':None,'titles_filename':'position_titles.csv',
        'data':None,'filename':'jobopenings.csv'}

generic_titles = ['engineer','manager','developer','officer','designer','research','controller','supervisor',
                  'operator','assistant','consultant','scientist','analyst','machinist',
                  'programmer','architect','technician','postdoctor','artist','secretary','administrator',
                 'superintendent','coordinator','surveyor','representative','writer','graduate','counsellor',
                 'coach','advisory','teacher','partner']

modifiers = ['technical','site','development','technology','production','apac','administrative',
            'asia pacific','singapore','team', 'applications','application','system',
            'excellence','integrity','country','performance','management','strategy','southeast asia','asia',
             'big','enterprise','experience','global','company','professional','group','solution','service',
             'practice','success','creative','commercial','greater','region','protocol','center','factor',
             'deployment','regional','china','korea','indonesia','vietnam','myanmar','india',
            'japan','laos','thailand','asean']

fields = ['qa','qc','civil','electrical','construction','structural','physical','business','building',
          'safety','piping','facilities','utility','trading','investment','commissioning','product',
          'hardware','mining','web','software','maintenance','firmware','python','customer',
          'machine learning','deep learning','automation','robotics','human factors','hse','rotating',
          'project','schedule','planning','data','validation','verification','digital','optical',
          'computer science','failure analysis','fixed equipment',
         'microcontroller','plant','cyber security','machine','sales','wireless','power','energy',
         'microsoft dynamics','ui ux','ux ui','beauty','hyperion','actuarial','financial','amazon',
         'apple','google','workday','robotic','cybersecurity','agile','security','blast','health','environmental',
         'telecom','media','engagement','account','wealth','asset','analytics','client','reliability','java',
         'blockchain','intelligence','plc','geophysicist','renewable','carbon','footprint','farm','sustainability',
          'instrument','hairstyl','microbiologist','cloud','ecommerce']

ranks = ['senior','junior','sr','principal','lead','fellow','associate','chief','vice president','president',
         'specialist','staff','mgrs','support','vp','executive','head','director']

tagLists = {'generic':generic_titles, 'modifier': modifiers, 'field':fields, 'rank':ranks}

#01 download stopwords

def nltk_load():
    try:
        _create_unverified_https_context = ssl._create_unverified_context
    except AttributeError:
        pass
    else:
        ssl._create_default_https_context = _create_unverified_https_context

    nltk.download('stopwords')

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

def load_jobs():
    global jobs
    jobs['data'] = pd.read_csv(jobs['filename'])

def cleanup_job_titles():
    global jobs
    titledata = pd.DataFrame({'clean title': jobs['data'].apply(
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
        return residual,hashStr
    else:
        return residual, extracted

def classify_title(titleStr):
    residual = titleStr
    tagHashes = []
    for tagList in [generic_titles, modifiers, fields, ranks]:
        residual, tagHash = extractTags(residual,tagList)
        tagHashes.append(tagHash.strip())
    generic = tagHashes[0]; modify = tagHashes[1]; field = tagHashes[2]; rank = tagHashes[3]
    return residual.strip(), generic, modify, field, rank

def extract_classify_titles():
    global jobs
    titledata = jobs['titles']
    titledata['residual'], titledata['generic'], titledata['modifier'], titledata['field'], titledata['rank']= \
        zip(*titledata['clean title'].map(classify_title))
    jobs['titles'] = titledata.copy()

def run_jobtitle_report():
    load_jobs()
    cleanup_job_titles()
    extract_classify_titles()
    jobs['titles'].to_csv(jobs['titles_filename'])
