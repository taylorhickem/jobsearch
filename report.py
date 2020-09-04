### this is a script for running reports using agent.JobSearchWebsite
###

# load packages
import agent
import sys
import time
import datetime as dt
import bs4
import re
import datetime as dt
import pandas as pd
import gsheet.api as gs

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

def get_pagesource(salaryLevel,category,page=0):
    global jobsite
    qryURL = jobsite.jobsearch_URLquery(salaryLevel, category, jobsite.employmentType,
                                   page=page)
    jobsite.driver.get(qryURL)
    time.sleep(2)
    pageStr = jobsite.driver.page_source
    return pageStr

def get_job_fromcard(cardObj):
    #salary
    def get_salaryHigh_fromcard(cardObj):
        salary_divTag = 'lh-solid' #unique tag identifier for the salary information
        divTags = cardObj.find_all('div')
        salaryDiv = [y for y in [x for x in divTags if
                                 x.has_attr('class')] if salary_divTag in y['class']][0]
        salaryHighStr = salaryDiv.text.split('to')[1]  #$8,000 (str)
        salaryHigh = int(salaryHighStr.replace(',', '').replace('$', '')) #8000 (int)
        return salaryHigh

    #title
    def get_position_title_fromcard(cardObj):
        title_keyword = 'job-title' #unique tag identifier
        titleHeader = [y for y in cardObj.find_all('h1') if title_keyword in str(y)][0]
        leftbloc = 'data-cy="job-card__job-title">'
        rightbloc = '</h1>'
        titleStr = re.search(leftbloc + '(.*)' + rightbloc, str(titleHeader)).group(1)
        return titleStr

    #posted date
    def get_posted_date_fromcard(cardObj):
        posted_keyword = 'last-posted-date' #unique tag identifier
        postedSection = [y for y in cardObj.find_all('section') if posted_keyword in str(y)][0]
        leftbloc = 'data-cy="job-card__last-posted-date">'
        rightbloc = '</span></section>'
        postedStr = re.search(leftbloc + '(.*)' + rightbloc, str(postedSection)).group(1)
        leftbloc2 = 'Posted '
        daysStr_1 = re.search(leftbloc2 + '(.*)', postedStr).group(1)

        #convert from x days ago to datetime.date
        todayDate = dt.datetime.today().date()
        if daysStr_1 == 'today':
            postedDate = todayDate
        else:
            rightbloc2 = ' days ago'
            dayShift = int(re.search('(.*)' + rightbloc2, daysStr_1).group(1))
            postedDate = todayDate-dt.timedelta(days=dayShift)
        return postedDate

    #company name
    def get_company_name_fromcard(cardObj):
        company_keyword = 'company-hire-info__company' #unique tag identifier
        companyP = [y for y in cardObj.find_all('p') if company_keyword in str(y)][0]
        leftbloc = 'data-cy="company-hire-info__company">'
        rightbloc = '</p>'
        companyStr = re.search(leftbloc + '(.*)' + rightbloc, str(companyP)).group(1)
        return companyStr

    #job id
    def get_jobid_fromcard(cardObj):
        url_keyword = 'JobCard__card' #unique tag identifier
        urlA = [y for y in cardObj.find_all('a') if url_keyword in str(y)][0]
        leftbloc = 'href="/job/'
        rightbloc = '"><div class="w-80-l w-100 flex flex-wrap'
        prjidStr = re.search(leftbloc + '(.*)' + rightbloc, str(urlA)).group(1)
        return prjidStr

    jobResult = {}
    jobResult['salaryHigh'] = get_salaryHigh_fromcard(cardObj)
    jobResult['position_title'] = get_position_title_fromcard(cardObj)
    jobResult['posted_date'] = get_posted_date_fromcard(cardObj)
    jobResult['company_name'] = get_company_name_fromcard(cardObj)
    jobResult['jobid'] = get_jobid_fromcard(cardObj)
    return jobResult

def jobs_from_cards():
    salaryLevel = 5000; category = 'Engineering'
    csvfilename = 'jobopenings.csv'
    cardTag = 'job-card-'

    # get page source and pageSoup object
    cardcount = 1 ; page = 0
    while cardcount>0:
        pageStr = get_pagesource(salaryLevel, category, page)
        pageSoup = bs4.BeautifulSoup(pageStr, "html5lib")

        # list of cards using the tag 'job-card-'
        cards = [y for y in [x for x in pageSoup.find_all('div')
                             if x.has_attr('id')] if cardTag in y['id']]
        cardcount = len(cards)
        if cardcount>0:
            #create DataFrame object from card objects
            if page==0:
                jobs = pd.DataFrame.from_records([get_job_fromcard(x) for x in cards])
            else:
                morejobs = pd.DataFrame.from_records([get_job_fromcard(x) for x in cards])
                jobs= jobs.append(morejobs)
        page = page + 1

    jobs.to_csv(csvfilename)
    nowtimeStr = dt.datetime.strftime(dt.datetime.now(), '%Y-%m-%d %H:%M:%S')
    print('report created at %s' % nowtimeStr)

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
    categories = ['Consulting','Engineering','Design']
    #categories = ['Consulting','Engineering','Design','Sciences / Laboratory / R&D','Education and Training','Manufacturing',
    #              'Information Technology','Healthcare / Pharmaceutical', 'Logistics / Supply Chain',
    #              'Risk Management','Others']
    salaryLevels = [6000]
    jobsite.set_report_parameters(salaryLevels,categories)
    jobsite.update_jobRecords()
    nowtimeStr = dt.datetime.strftime(dt.datetime.now(), '%Y-%m-%d %H:%M:%S')
    print('report created at %s' % nowtimeStr)

#02 update report with google spreadsheet
def post_jobs_to_gsheet(jobs):
    wkbid = '1JiB-ofvyimIOZ9vVxF22xIyXybIP5FCyo6N_x-pvmCs'
    rngid = 'MCF_openings!A2:E'
    engine = gs.SheetsEngine()

    #values is a 2D list [[]]
    values = jobs.values.astype('str').tolist()
    engine.clear_rangevalues(wkbid,rngid)
    #write values - this method writes everything as a string
    engine.set_rangevalues(wkbid,rngid,values)

def update_jobs_report(from_file=False):
    #01 query job openings from MyCareerFutures website
    if from_file:
        jobs=pd.read_csv('jobopenings.csv')
    else:
        load()
        categories = ['Consulting','Engineering','Design']
        salaryLevels = [6000]
        jobsite.set_report_parameters(salaryLevels,categories)
        jobsite.update_jobRecords()
        jobs = jobsite.jobs['records']

    #02 post the results to the google spreadsheet
    post_jobs_to_gsheet(jobs)
    print('jobs report updated.')

# customize how this script runs

def autorun():
    if len(sys.argv)>1:
        process_name = sys.argv[1]
        if process_name == 'update_jobs_report':
            update_jobs_report()
        elif process_name == 'update_jobRecords':
            update_jobRecords()
    else:
        print('no report specified')

if __name__ == "__main__":
    autorun()

