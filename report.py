### this is a script for running reports using agent.JobSearchWebsite
###

# load packages
import agent
import datetime as dt
import bs4

# load an instance of JobSearchWebsite --> jobsite
jobsite = None
qryResult = None
def load():
    global jobsite
    if jobsite is None:
        jobsite = agent.JobSearchWebsite()

# 01.01 run one qry
def run_searchQry(salaryLevel,category):
    global qryResult
    qryResult= jobsite.jobsearchQuery(salaryLevel, category, jobsite.employmentType)

def sample_qry():
    salaryLevel = 5000 ; category = 'Engineering'
    run_searchQry(salaryLevel,category)

def debug_emptyQry():
    global jobsite
    load()
    js = jobsite
    salaryLevel = 5000;    category = 'Engineering'
    qryURL = js.jobsearch_URLquery(salaryLevel, category, js.employmentType,
                                   page=js.search_defaults['page'])
    js.driver.get(qryURL)
    pageStr = js.driver.page_source
    pageSoup = bs4.BeautifulSoup(pageStr, "html5lib")

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

# customize how this script runs

def autorun():
    load()
    run_screening_report()

if __name__ == "__main__":
    autorun()