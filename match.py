from agent import JobSearchWebsite
import database as db
import text as tx
import pandas as pd

# load an instance of JobSearchWebsite --> jobsite
jobsite = None
jobs = None
titles = None

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

def update_tags():
    global titles
    db.update_tags()
    tags = db.get_tags()
    tx.load_tags(tags)
    jobs = db.get_jobs()
    tx.load_jobs(jobs)
    tx.run_jobtitle_report()
    titles = tx.jobs['titles'].copy()
