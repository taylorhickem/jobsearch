from agent import JobSearchWebsite
import database as db
import text as tx
import pandas as pd
import datetime as dt
import report

# load an instance of JobSearchWebsite --> jobsite
jobsite = None
jobs = None
titles = None
matches = None
screened = None

FILTER_SETTINGS = {
    'age_weeks':3,
}

def load_jobsite():
    global jobsite, jobs
    if jobsite is None:
        jobsite = JobSearchWebsite()
        jobs = jobsite.jobs['records'].copy()

def load_db():
    global jobs
    db.load()
    jobs = db.get_jobs()

def get_match_report():
    global jobs
    tx.load_jobs(jobs)
    tx.run_jobtitle_report()
    titles = tx.jobs['titles'].copy()

#get frequency distribution of tags
def get_tag_counts(tag_type,norm=False):
    #unpack the tags which are separated by colon and convert into a dataframe
    tag_df  = pd.DataFrame({tag_type:[x for y in titles[tag_type].tolist()
                                      for x in y.split(':') if not x=='']})
    #pivot the dataframe
    counts = pd.pivot_table(tag_df, index=tag_type, aggfunc='size').sort_values(ascending=False)
    if norm:
        counts = counts/sum(counts)
    return counts

def keyword_tags():
    db.update_tags()
    tags = db.get_tags()
    return tags

def extracted_tags():
    tags = keyword_tags()
    tx.load_tags(tags)
    jobs = db.get_jobs()
    tx.load_jobs(jobs)
    tx.run_jobtitle_report()
    titles = tx.jobs['titles'].copy()
    return titles

def screen_jobs():
    ''' screens jobs based on matching keyword tags.
    The process is divided into two general steps - scoring and filtering and 5 sub-processes
    - cleanup title and extract tags, score the clean title from extracted tags.
    The screened table drops the reject scores and filters for current applications based on posted_date.
    The inputs are the job and tag tables and there are two outputs
    - an updated sqlite table ‘match’ and the screened jobs posted to gsheet.'''

    #01 cleanup title, extract tags, score title
    #02 store the match_auto score in the sqlite match table
    update_matches()
    #03 drop the relected positions, filter for most recent posts <=3 weeks
    #04 push update to gsheet
    update_screened()

def score_positions():
    ''' scores positions using text.py to cleanup title, extract tags
    and compute score from extracted tags
    '''
    global jobs, titles
    tags = keyword_tags()
    tx.load_jobs(jobs)
    tx.load_tags(tags)
    tx.run_jobtitle_report()
    titles = tx.jobs['titles'].copy()

def update_matches():
    '''updates the match table from the titles table by dropping fields
    '''
    global titles, matches
    score_positions()
    #fields to keep : jobid, clean_title, match_auto
    fields = ['jobid','clean_title','match_auto']
    matches = titles[fields].copy()
    db.update_match(matches)

def add_weeks(df):
    df['date'] = df.apply(lambda x: dt.datetime.strptime(
        x.posted_date, '%Y-%m-%d').date(),axis=1)
    del df['posted_date']
    df.rename(columns={'date': 'posted_date'}, inplace=True)
    df['monday'] = report.get_mondays(df['posted_date'])
    monday = report.get_monday(dt.datetime.today().date())
    df['week'] = df.apply(lambda x: int((monday - x.monday).days / 7), axis=1)
    del df['monday']
    return df

def update_screened():
    ''' drops the rejected positions and filters for recent based on posted_date
    '''
    global titles, jobs, screened
    weeks = FILTER_SETTINGS['age_weeks']
    fields = ['match_auto','clean_title','company_name','salaryHigh','week',
              'posted_date','position_title','urlid','jobid']
    screened = jobs.merge(titles[['jobid', 'clean_title', 'match_auto']], on='jobid')
    screened = add_weeks(screened)
    recent = screened[screened['week'] <= weeks]
    keep = recent[recent.match_auto != -1]
    screened = keep[fields].sort_values(['week', 'match_auto'], ascending=(True, False))
    #post to gsheet
    db.post_to_gsheet(screened,'screened')