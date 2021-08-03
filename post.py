# import dependencies
#----------------------------------------------------
import datetime as dt
import pandas as pd

import database as db
#----------------------------------------------------
# module variables
#----------------------------------------------------
posts = None
jobs = None
profiles = None

#----------------------------------------------------
# interfaced procedures
#----------------------------------------------------
def load():
    global jobs, profiles
    db.load()
    if db.table_exists('job'):
        jobs = db.get_table('job')
    if db.table_exists('profile'):
        profiles = db.get_table('profile')


def update_new_posts():
    global posts
    # 01 load new posts table from gsheet

    print('loading posts..')
    posts = db.get_sheet('new_posts')

    # 02 [PLACEHOLDER ONLY] cleanup auto-fill (or drop) required null fields

    # 03 add jobid
    posts['jobid'] = posts.apply(lambda x: jobid_from_post(
        x['source'], x['timestamp'], x['posted_date']), axis=1)

    # 4 get new jobids from difference of ids in posts tbl and jobs tbl
    new_jobids = set(posts['jobid']).difference(set(jobs['jobid']))
    print('%s new posts found' % len(new_jobids))

    if len(new_jobids) > 0:
        new_posts = posts[posts.jobid.isin(new_jobids)].copy()

        # 05 create new rows for jobs and profiles tables and update sqlite tables
        new_jobs = jobs_from_posts(new_posts)
        if len(new_jobs) > 0:
            db.update_table(new_jobs, 'job', True)
            print('added %s new posts' % len(new_jobs))

        new_profiles = profiles_from_posts(new_posts)
        if len(new_profiles) > 0:
            db.update_table(new_profiles, 'profile', True)


#----------------------------------------------------
# dependent procedures
#----------------------------------------------------
def jobs_from_posts(posts_tbl):
    global jobs
    new_jobs = []
    if len(posts_tbl) > 0:
        new_jobs = posts_tbl.copy()
        new_jobs['src_methodid'] = 1
        new_jobs['urlid'] = None
        new_jobs['posted_date'] = new_jobs['posted_date'].apply(
            lambda x: dt.datetime.strftime(x, '%Y-%m-%d'))
        new_jobs = new_jobs[jobs.columns].copy()
    return new_jobs


def profiles_from_posts(posts_tbl):
    global profiles
    new_profiles = []
    if len(posts_tbl) > 0:
        new_profiles = posts_tbl.copy()
        new_profiles['mcf_ref'] = None
        # auto-fill closing date if empty
        new_profiles['closing_date'] = new_profiles.apply(
            lambda x: update_closing_date(x['closing_date'], x['posted_date']), axis=1)
        new_profiles = new_profiles[profiles.columns].copy()
    return new_profiles


def jobid_from_post(source, timestamp_str, posted_date):
    time_str = timestamp_str[-8:].replace(':', '')
    posted_str = dt.datetime.strftime(posted_date, '%Y-%m-%d')
    jobid = '-'.join([source, time_str, posted_str])
    return jobid


def update_closing_date(cl_date, post_date):
    closing_date = cl_date
    if pd.isnull(cl_date):
        closing_date = post_date + dt.timedelta(days=30)
    return closing_date
#----------------------------------------------------
# END
#----------------------------------------------------