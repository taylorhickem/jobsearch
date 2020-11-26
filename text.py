#import nltk
import ssl
import re
from nltk.corpus import stopwords
import string
import pandas as pd
import numpy as np
import database as db

from sklearn.linear_model import LogisticRegression
from sklearn.feature_extraction.text import CountVectorizer

#----------------------------------------------------
#Static variables
#----------------------------------------------------

tag_sheets = {}
tag_tbls = {}

#----------------------------------------------------
#Setup, initialization
#----------------------------------------------------

def load():
    'load tags and job profiles from gsheet and sql'
    db.load()
    load_gsheet()
    load_sql()

def load_gsheet():
    load_tags_gsheet()

def load_sql():
    load_tags_sql()

def load_tags_gsheet():
    global tag_sheets
    title_tags = db.get_sheet('title_tags')
    junk_tags = db.get_sheet('junk_tags')
    rank_tags = db.get_sheet('rank_tags')
    industries = db.get_sheet('industries')
    tag_sheets = {'title':{'data':title_tags,
                           'name':'title_tags'},
                  'rank':{'data':rank_tags,
                          'name':'rank_tags'},
                  'junk':{'data':junk_tags,
                          'name':'junk_tags'},
                  'ic': {'data':industries,
                         'name':'industries'}
                  }

def load_tags_sql():
    global tag_tbls
    title_tbl = db.get_table('title_tag')
    junk_tbl = db.get_table('junk_tag')
    rank_tbl = db.get_table('rank_tag')
    ic_tbl = db.get_table('industry_classification')
    tag_tbls = {'title':{'data':title_tbl,
                         'name':'title_tag'},
                'rank':{'data':rank_tbl,
                        'name':'rank_tag'},
                'junk':{'data':junk_tbl,
                        'name':'junk_tag'},
                'ic': {'data':ic_tbl,
                       'name':'industry_classification'}
                }

# ----------------------------------------------------
# Procedures
# ----------------------------------------------------

def push_tag_gsheets_to_sql(skip=[]):
    for tag_type in tag_sheets:
        if not tag_type in skip:
            db.update_table(tag_sheets[tag_type]['data'],
                            tag_tbls[tag_type]['name'],append=False)

# ----------------------------------------------------
# Text analysis
# ----------------------------------------------------

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


def selective_token_cleanup(strValue,cleanup_list,strict_word=False):
    for tag in cleanup_list:
        if tag in strValue:
            if strict_word:
                strValue = strValue.replace(' '+tag+' ',' ')
            else:
                strValue = re.sub(' ('+tag+')|('+tag+') ',' ',strValue)
    trimmed = strValue.strip()
    return trimmed

def remove_ampersand(strValue):
    strValue = strValue.replace('mampe','me')
    strValue = strValue.replace('rampd','rd')
    strValue = strValue.replace('oampg','og')
    strValue = strValue = re.sub(' (amp)|(amp) ',' and ',strValue)
    trimmed = strValue.strip()
    return trimmed

def remove_stopwords(strValue,strict_word=True):
    wordlist = stopwords.words('english')
    cleanStr = selective_token_cleanup(strValue,wordlist,strict_word=strict_word)
    return cleanStr

def cleanup(strValue):
    # keep only alphabet characters
    letterStr = re.sub('[^a-zA-Z ]+','',strValue)
    # lower case only
    lowerStr = letterStr.lower()
    # remove ampersand &
    noamp = remove_ampersand(lowerStr)
    # remove extra spaces on ends (not inbetween)
    trimmed = noamp.strip()
    return trimmed

def remove_junk(strValue):
    cleanStr = cleanup(strValue)
    nostop = remove_stopwords(cleanStr)
    junkwords = tag_tbls['junk']['data']['tag'].values
    cleanStr = selective_token_cleanup(nostop,junkwords)
    trimmed = cleanStr.strip()
    return trimmed

def derank(strValue):
    rankwords = tag_tbls['rank']['data']['tag'].values
    cleanStr = selective_token_cleanup(strValue,rankwords)
    trimmed = cleanStr.strip()
    return trimmed

def add_clean_deranked_titles(profiles):
    #01 clean-up, dejunk title
    profiles['clean_title'] = profiles['position_title'].apply(lambda x:remove_junk(x))
    #02 derank title
    profiles['deranked_title'] = profiles['clean_title'].apply(lambda x:derank(x))
    return profiles

def get_bigram_matrix(titles):
    vect = CountVectorizer(min_df=5, ngram_range=(2, 2), analyzer='word').fit(titles)
    feature_names = np.array(vect.get_feature_names())
    X_v = vect.transform(titles)
    return (feature_names, X_v)

def get_new_bigrams(profiles,export=False):
    #01 clean-up, dejunk, derank title
    profiles = add_clean_deranked_titles(profiles)
    #03 get bigram matrix using CountVectorizer (sklearn)
    feature_names, X_v = get_bigram_matrix(profiles.deranked_title)
    #05 create the bigram table
    feature_counts = [np.sum(X_v[:, x]) / len(profiles) for x in range(len(feature_names))]
    bigrams = pd.DataFrame({'tag': feature_names, 'count': feature_counts})
    bigrams.sort_values('count', ascending=False, inplace=True)
    if export:
        bigrams.to_csv('bigrams.csv',index=False)
    return bigrams

# ----------------------------------------------------
# ***
# ----------------------------------------------------


