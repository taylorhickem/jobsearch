### this is a script for running reports using agent.JobSearchWebsite
###

# load packages
import mcf_profile
import agent
import sys
import math
import time
import datetime as dt
import bs4
import re
import pandas as pd
import database as db
import match

# load an instance of JobSearchWebsite --> jobsite
jobsite = None
qryResult = None
DATE_FORMAT = '%Y-%m-%d'
SEARCH_CONFIG = {}


def load(db_only=False):
    global jobsite
    if not db_only:
        if jobsite is None:
            jobsite = agent.JobSearchWebsite()
    db.load()


def load_config():
    SEARCH_CONFIG = db.CONFIG_FILES['search']['data']

# 01.01 run one qry
def run_searchQry(salaryLevel,category):
    global qryResult
    qryResult= jobsite.jobsearchQuery(salaryLevel, category, jobsite.employmentType)


def sample_qry():
    salaryLevel = 5000 ; category = 'Engineering'
    run_searchQry(salaryLevel,category)


def get_pagesource(salaryLevel,category,page=0):
    global jobsite
    qryURL = jobsite.jobsearch_URLquery(salaryLevel, category, jobsite.employmentType,
                                   page=page)
    jobsite.driver.get(qryURL)
    time.sleep(2)
    pageStr = jobsite.driver.page_source
    return pageStr

# 01.03 run screening report
def run_screening_report():
    #set the job type categories and salary levels for the report
    categories = ['Sciences%20%2F%20Laboratory%20%2F%20R%26D','Consulting','Engineering','Design']
    #categories = ['Consulting','Engineering','Design','Sciences / Laboratory / R&D','Education and Training','Manufacturing',
    #              'Information Technology','Healthcare / Pharmaceutical', 'Logistics / Supply Chain',
    #              'Risk Management','Others']
    salaryLevels = [2000,3000,4000,5000,6000,7000,8000]
    jobsite.set_report_parameters(salaryLevels,categories)
    jobsite.run_report()
    nowtimeStr = dt.datetime.strftime(dt.datetime.now(), '%Y-%m-%d %H:%M:%S')
    print('report created at %s' % nowtimeStr)

# 01.04 run job records report
def update_jobRecords():
    keywords = SEARCH_CONFIG['search']['keywords']
    #focus = ['Consulting','Engineering','Professional Services',
    #              'Science','Environment','Information Technology','Manufacturing']
    salary_min = SEARCH_CONFIG['search']['salary_min']
    jobsite.set_report_parameters([salary_min],keywords)
    jobsite.update_jobRecords()
    nowtimeStr = dt.datetime.strftime(dt.datetime.now(), '%Y-%m-%d %H:%M:%S')
    print('report created at %s' % nowtimeStr)


def update_jobs_report(from_file=False):
    #01 query job openings from MyCareerFutures website

    if from_file:
        jobs=pd.read_csv('jobopenings.csv')
    else:
        starttime = time.time()
        load()
        jobCount_i = len(db.get_jobs())
        categories = ['Consulting', 'Engineering', 'Professional Services',
                      'Science', 'Environment', 'Information Technology', 'Manufacturing']
        salaryLevels = [5000]
        jobsite.set_report_parameters(salaryLevels,categories)
        jobsite.update_jobRecords()
        jobs = jobsite.jobs['records']
        match.load()
        screen_jobs()
        new_jobs = len(db.get_jobs())-jobCount_i
        elapsed = time.time()-starttime
        e_min = math.floor(elapsed/60)
        e_sec = elapsed-e_min*60
    print('added %d new jobs in %d min :%d sec' % (new_jobs,e_min,e_sec))


def screen_jobs():
    match.load()
    match.screen_jobs()


def update_job_profiles(limit=200):
    #200 records ~ 15 minute runtime
    mcf_profile.load()
    mcf_profile.update_job_profiles(limit)
    screen_jobs()


def get_monday(dateValue):
    return dateValue-dt.timedelta(days=dateValue.weekday())


def get_mondays(date_series):
    return date_series.apply(lambda x:x-dt.timedelta(days=x.weekday()))


def get_weeknums(date_str_series):
    def get_monday(dateValue):
        return dateValue-dt.timedelta(days=dateValue.weekday())
    def get_weeknum(dateValue,this_monday):
        return 1/7*(this_monday-(dateValue-dt.timedelta(days=dateValue.weekday()))).days
    def convert_date_series(date_series):
        return date_series.apply(lambda x:dt.datetime.strptime(x,DATE_FORMAT).date())
    this_monday = get_monday(dt.datetime.now().date())
    date_series = convert_date_series(date_str_series)
    weeknums = date_series.apply(lambda x:get_weeknum(x,this_monday))
    return weeknums


def get_openings_byweek():
    load(db_only=True)
    jobs = db.get_jobs()
    jobs['date'] = jobs.apply(lambda x: dt.datetime.strptime(
        x.posted_date, '%Y-%m-%d').date(),axis=1)
    del jobs['posted_date']
    jobs.rename(columns={'date': 'posted_date'}, inplace=True)
    jobs['monday'] = get_mondays(jobs['posted_date'])
    byweek = pd.pivot_table(jobs, index='monday', aggfunc='size')
    return byweek

# customize how this script runs

def autorun():
    if len(sys.argv) > 1:
        process_name = sys.argv[1]
        if process_name == 'update_jobs_report':
            update_jobs_report()
        elif process_name == 'update_jobRecords':
            update_jobRecords()
        elif process_name == 'screen_jobs':
            screen_jobs()
        elif process_name == 'update_job_profiles':
            if len(sys.argv)>2:
                limit = int(sys.argv[2])
                update_job_profiles(limit)
            else:
                update_job_profiles()
    else:
        print('no report specified')


if __name__ == "__main__":
    autorun()

