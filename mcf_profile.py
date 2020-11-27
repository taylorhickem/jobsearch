import time
import datetime as dt
import pandas as pd
import bs4

import database as db
from agent import JobSearchWebsite

jobsite = None
profiles = None
mainURL = ''
FIELD_CONFIG = {
    'mcf_ref':{'tag_class':'span',
               'html_keyword':'jobinfo__jobpostid',
               'drop_chr':'',
               'type':'string'},
    'closing_date':{'tag_class':'span',
               'html_keyword':'expiry_date',
               'drop_chr':'Closing on ',
                'datetime_format':'%d %b %Y',
               'type':'date'},
    'years_experience':{'tag_class':'p',
               'html_keyword':'min_experience',
               'drop_chr':'',
               'type':'str'},
    'applicants':{'tag_class':'span',
               'html_keyword':'num_of_applications',
               'drop_chr':' application',
               'type':'int'},
    'industry_classification':{'tag_class':'p',
               'html_keyword':'job-categories',
               'drop_chr':'',
               'type':'string'},
    'description':{'tag_class':'div',
               'subclass': 'id',
               'html_keyword':'description-content',
               'drop_chr':'',
               'return_type':'text',
               'type':'string'},
}

def load(db_only=False):
    global jobsite, mainURL, profiles
    if not db_only:
        if jobsite is None:
            jobsite = JobSearchWebsite()
            mainURL = jobsite.mainURL
    db.load()
    if db.table_exists('profile'):
        profiles = db.get_table('profile')

def update_job_profiles(limit=200):
    profileRcds= [] ; failed = []
    idList = get_profile_ids().values.tolist()
    if len(idList)>limit:
        idList = idList[:limit]
    for prfid in idList:
        try:
            rcd = get_profileRecord(prfid[1], prfid[0], mainURL)
            profileRcds.append(rcd)
        except:
            print('error encountered while trying to parse profile page for job %s ' % prfid[0])
            failed.append(prfid)
    num_failed = len(failed)
    if num_failed>0:
        print('%d profile(s) encountered an error' % num_failed)
    profiles = pd.DataFrame.from_records(profileRcds)
    update_db(profiles)

def get_profile_ids():
    global profiles
    ''' minus set operation from tables 'job' and 'profile'
    to find the job openings which haven't yet had their profiles recorded
    '''
    #get job ids from job table
    jobs = db.get_jobs().sort_values('posted_date',ascending=False)
    #get job ids from profile table (first check if profile table exists)
    #this is local working copy which will be modified and then at the end pushed back to the db
    if profiles is None:
        profileids = jobs[['jobid', 'urlid']].copy()
    else:
        # compare ids
        profileids = jobs[jobs['jobid'].isin(profiles['jobid']) == False][['jobid', 'urlid']].copy()
    return profileids

def get_profileRecord(urlid,jobid='',mainURL=None):
    url = profile_url(urlid,mainURL)
    pageSoup = query_url(url)
    def get_profile_fieldValue(field_name):
        fieldValue = None
        fldcfg = FIELD_CONFIG[field_name]
        fieldStr = get_tag_element(pageSoup,fldcfg['tag_class'],
                                   fldcfg['html_keyword'],fldcfg['drop_chr'])
        if not fieldStr is None:
            if fldcfg['type'] == 'int':
                fieldValue = int(fieldStr)
            elif fldcfg['type'] == 'date':
                fieldValue = dt.datetime.strptime(fieldStr,fldcfg['datetime_format']).date()
            else:
                fieldValue = fieldStr
        return fieldValue

    #extract fields
    mcf_ref  = get_profile_fieldValue('mcf_ref')
    closing_date  = get_profile_fieldValue('closing_date')
    yrsexpStr = get_profile_fieldValue('years_experience')
    applicantsInt = get_profile_fieldValue('applicants')
    industry_classification = get_profile_fieldValue('industry_classification')

    #years of experience (int) plural and singular case
    if not yrsexpStr is None:
        yrsexpInt = int(yrsexpStr.replace(' year exp','').replace(' years exp',''))
    else:
        yrsexpInt = None

    #description (string)
    fldcfg = FIELD_CONFIG['description']
    desStr = get_tag_element(pageSoup, fldcfg['tag_class'],
                               fldcfg['html_keyword'],
                               fldcfg['drop_chr'],
                               subclass=fldcfg['subclass'],
                               return_type=fldcfg['return_type'])

    rcd = {'jobid':jobid,
           'url':url,
           'mcf_ref':mcf_ref,
           'closing_date':closing_date,
           'years_experience':yrsexpInt,
           'applicants':applicantsInt,
           'industry_classification':industry_classification,
           'description':desStr
           }
    return rcd

def profile_url(urlid,mainURL=None):
    if mainURL is None:
        mainURL = jobsite.mainURL
    url = mainURL + 'job/' + urlid
    return url

def get_tag_element(tagObj,tag_class,html_keyword,drop_chr='',subclass=None,return_type='string'):
    element = None
    if subclass is None:
        leaftags = [y for y in tagObj.find_all(tag_class) if html_keyword in str(y)]
    else:
        leaftags = [y for y in [x for x in tagObj.find_all(tag_class) if
                                x.has_attr(subclass)] if html_keyword in y[subclass]]
    if len(leaftags)>0:
        if return_type =='element':
            element = leaftags
        if return_type =='text':
            element = leaftags[0].get_text()
        if return_type=='contents':
            element = leaftags[0].contents
        elif return_type =='string':
            raw_element = leaftags[0].string
            if drop_chr != '':
                element = raw_element.replace(drop_chr,'').replace('s','')
            else:
                element = raw_element
    return element

def query_url(url):
    jobsite.driver.get(url)
    time.sleep(2)
    pageStr = jobsite.driver.page_source
    pageSoup = bs4.BeautifulSoup(pageStr, jobsite.parserStr)
    return pageSoup

def update_db(new_profiles=None):
    global profiles
    #database compare and update using pandas (instead of sqlalchemy)
    if not new_profiles is None:
        if len(new_profiles)>0:
            if not profiles is None:
                profiles=profiles.append(new_profiles)
                profiles.set_index('jobid',inplace=True)
                profiles.drop_duplicates(inplace=True)
                profiles.reset_index(inplace=True)
            else:
                profiles = new_profiles
    #push the new 'profiles' records to the sqlite database
    db.update_table(profiles,'profile',append=False)
