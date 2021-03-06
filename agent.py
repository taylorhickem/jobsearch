from selenium import webdriver
import bs4
import pandas as pd
import re
import timeit
import numpy as np

import os
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
import datetime as dt
from timeit import default_timer as timer
import time
import database

chrome_options = Options()
chrome_options.add_argument("--headless")
#chrome_options.binary_location = '/Applications/Google Chrome

files = {'job_openings':'jobopenings.csv'}

class JobSearchWebsite(object):
    report_folder = ''
    data = None
    data_source = ''
    report = None
    driver = None
    pageSoup = None
    name = ''
    mainURL = 'https://'
    parserStr = "html5lib"
    resultElementTag = 'span'
    resultTag = 'search-results'
    resultMarkers = ['<div data-cy="search-result-headers">', 'jobs found']
    cardTag = 'job-card-'
    jobs = {'records':None,'filename':None}
    cardsPerPage = 20
    searchFieldsd = {}
    search_defaults = {}
    salaryLevels = []
    categories = []
    employmentType = ''
    location = ''
    reportFields = ['date', 'source', 'job location', 'employment type', 'job category',
                    'monthly salary', 'matching jobs', 'total jobs']

    def __init__(self, name='MyCareerFutures', mainURL='https://www.mycareersfuture.sg/',
                 searchFields={'salary', 'employmentType', 'category'},
                 search_defaults={'sort': 'new_posting_date', 'page': 0},
                 load_driver=True,data_source='db'):
        global files
        self.name = name
        self.mainURL = mainURL
        self.searchFields = searchFields
        self.search_defaults = search_defaults
        self.data_source = data_source
        self.jobs['filename'] = files['job_openings']
        database.load()
        if load_driver:
            self.loadDriver()
        if os.path.exists(self.jobs['filename']):
            if data_source == 'db':
                self.jobs['records'] = database.get_jobs().copy()
            elif data_source == 'csv':
                self.jobs['records'] = pd.read_csv(self.jobs['filename'])

    def __del__(self):
        try:
            self.driver.quit()
        except:
            pass

    def loadDriver(self):
        self.driver = webdriver.Chrome(executable_path=os.path.abspath('chromedriver'), options=chrome_options)

    def set_report_parameters(self, salaryLevels, categories, employmentType='Full Time',
                              location='Singapore',
                              report_folder='C:\\Users\\taylo\\Helva\\05 Business Development\\03 active income'):
        self.salaryLevels = salaryLevels;
        self.categories = categories
        self.employmentType = employmentType;
        self.location = location
        self.report_folder = report_folder

    def run_report(self):
        # create list of job search records using jobsearchQuery()
        data = []
        report_date = dt.datetime.now().date()
        report_start = timer()
        for search in self.categories:
            for salary in self.salaryLevels:
                checkpoint = timer()
                #          date ,     source, location,         emp type, category, salary, matching jobs, jobs total
                qryResult = self.jobsearchQuery(salary, search, self.employmentType)
                queryJobs = qryResult['query jobs']
                totalJobs = qryResult['total jobs']
                rcdRow = [report_date, self.name, self.location, self.employmentType, search, salary, queryJobs, totalJobs]
                data.append(rcdRow)
            print('query complete for job %s in %.2f seconds' % (search, timer() - checkpoint))
        # create pandas dataframe for job search records and export to csv
        self.data = pd.DataFrame.from_records(data, columns=self.reportFields)
        self.data.to_csv(self.report_folder + '\\jobsearchdata.csv')

        # create pandas pivot table report from job search data and export to csv
        self.report = pd.pivot_table(self.data, index='job category', columns='monthly salary',
                                     values=['matching jobs'])
        self.report.to_csv(self.report_folder + '\\jobsearchreport.csv')
        print('job report complete in %.2f min' % (1 / 60 * (timer() - report_start)))

    def jobsearchQuery(self, salary=1000, search='Professional Services'):
        qryURL = self.jobsearch_URLquery(salary, search, page=self.search_defaults['page'])
        qryResult = self.get_searchResults(qryURL)
        return qryResult

    def url_query(self, main, filters=None, sort='new_posting_date', page=0):
        if not filters is None:
            queryFilters = [key + '=' + str(filters[key]).replace(' ', '%20') for key in filters]
            queryStr = '&'.join(queryFilters)
        else:
            queryStr = ''
        qURL = main + 'search?' + queryStr + '&sort=' + sort + '&page=' + str(page)
        return qURL

    def jobsearch_URLquery(self, salary, search, page=0):
        filters = {}
        filters['search'] = search;
        filters['salary'] = salary;
        qryURL = self.url_query(self.mainURL, filters, sort=self.search_defaults['sort'], page=page)
        return qryURL

    def refresh_pageSoup(self, qryURL):
        self.driver.get(qryURL)
        time.sleep(2)
        pageStr = self.driver.page_source
        self.pageSoup = bs4.BeautifulSoup(pageStr,self.parserStr)

    def get_searchResults(self, qryURL):
        self.refresh_pageSoup(qryURL)
        return self.searchresults_fromSoup(self.pageSoup)

    def searchresults_fromSoup(self, soupObj):
        elmList = soupObj.findAll(self.resultElementTag)
        divStr = [str(x.div) for x in elmList if self.resultTag in str(x)][0]
        markers = [divStr.find(self.resultMarkers[x]) for x in [0, 1]]
        resultStr = divStr[markers[0] + len(self.resultMarkers[0]):markers[1] - 1]
        if 'of' in resultStr:
            strPairs = [x.strip().replace(',', '') for x in resultStr.split('of')]
        else:
            strPairs = [x.strip().replace(',', '') for x in [resultStr,resultStr]]
        resPair = [0 if x == '' else int(x) for x in strPairs]
        if len(resPair) == 2:
            resDict = {'query jobs': resPair[0], 'total jobs': resPair[1]}
        else:
            resDict = {'query jobs': resPair[0], 'total jobs': resPair[0]}
        return resDict

    def get_jobRecord_fromcard(self,cardObj):
        # salary
        def get_salaryHigh(cardObj):
            salary_divTag = 'lh-solid'  # unique tag identifier for the salary information
            divTags = cardObj.find_all('div')
            salaryDiv = [y for y in [x for x in divTags if
                                     x.has_attr('class')] if salary_divTag in y['class']][0]
            salaryHighStr = salaryDiv.text.split('to')[1]  # $8,000 (str)
            salaryHigh = int(salaryHighStr.replace(',', '').replace('$', ''))  # 8000 (int)
            return salaryHigh

        # title
        def get_position_title(cardObj):
            title_keyword = 'job-title'  # unique tag identifier
            titleHeader = [y for y in cardObj.find_all('h1') if title_keyword in str(y)][0]
            leftbloc = 'data-cy="job-card__job-title">'
            rightbloc = '</h1>'
            titleStr = re.search(leftbloc + '(.*)' + rightbloc, str(titleHeader)).group(1)
            return titleStr

        # posted date
        def get_posted_date(cardObj):
            posted_keyword = 'last-posted-date'  # unique tag identifier
            postedSection = [y for y in cardObj.find_all('section') if posted_keyword in str(y)][0]
            leftbloc = 'data-cy="job-card__last-posted-date">'
            rightbloc = '</span></section>'
            postedStr = re.search(leftbloc + '(.*)' + rightbloc, str(postedSection)).group(1)
            leftbloc2 = 'Posted '
            daysStr_1 = re.search(leftbloc2 + '(.*)', postedStr).group(1)

            # convert from x days ago to datetime.date
            todayDate = dt.datetime.today().date()
            dayShift = 0
            if daysStr_1 == 'today':
                postedDate = todayDate
            elif daysStr_1 == 'yesterday':
                dayShift = 1
            else:
                rightbloc2 = ' days ago'
                try:
                    dayShift = int(re.search('(.*)' + rightbloc2, daysStr_1).group(1))
                except:
                    urlid = get_urlid(cardObj)
                    print('urlid: %s, original: %s, left filter: %s' % (urlid,postedStr, daysStr_1))

            postedDate = todayDate - dt.timedelta(days=dayShift)
            return postedDate

        # company name
        def get_company_name(cardObj):
            company_keyword = 'company-hire-info__company'  # unique tag identifier
            companyP = [y for y in cardObj.find_all('p') if company_keyword in str(y)][0]
            leftbloc = 'data-cy="company-hire-info__company">'
            rightbloc = '</p>'
            companyStr = re.search(leftbloc + '(.*)' + rightbloc, str(companyP)).group(1)
            return companyStr

        # url id
        def get_urlid(cardObj):
            url_keyword = 'JobCard__card'  # unique tag identifier
            urlA = [y for y in cardObj.find_all('a') if url_keyword in str(y)][0]
            leftbloc = 'href="/job/'
            rightbloc = '"><div class="w-80-l w-100 flex flex-wrap'
            prjidStr = re.search(leftbloc + '(.*)' + rightbloc, str(urlA)).group(1)
            return prjidStr

        # job id
        def get_jobid(job_dict):
            jobid = '-'.join([job_dict['source'],
                              job_dict['urlid'][-32:],
                              dt.datetime.strftime(job_dict['posted_date'],'%Y-%m-%d')])
            return jobid

        jobRecord = {}
        jobRecord['salaryHigh'] = get_salaryHigh(cardObj)
        jobRecord['position_title'] = get_position_title(cardObj)
        jobRecord['posted_date'] = get_posted_date(cardObj)
        jobRecord['company_name'] = get_company_name(cardObj)
        jobRecord['urlid'] = get_urlid(cardObj)
        jobRecord['source'] = self.name
        jobRecord['jobid'] = get_jobid(jobRecord)
        return jobRecord

    def jobRecords_query(self,salary, search):
        cardcount = 1; page = 0 ; jobs = None
        while cardcount > 0:
            qryURL = self.jobsearch_URLquery(salary, search, page)
            self.refresh_pageSoup(qryURL)

            # list of cards using the tag 'job-card-'
            cards = [y for y in [x for x in self.pageSoup.find_all('div')
                                 if x.has_attr('id')] if self.cardTag in y['id']]
            cardcount = len(cards)
            if cardcount > 0:
                # create DataFrame object from card objects
                rcds = []
                for x in cards:
                    try:
                        rcd = self.get_jobRecord_fromcard(x)
                        rcds.append(rcd)
                    except:
                        print('error encountered for card %s on page %d' % ( x['id'],page))
                morejobs = pd.DataFrame.from_records(rcds)
                if page == 0:
                    jobs = morejobs
                else:
                    jobs = jobs.append(morejobs)
            page = page + 1

        return jobs

    def update_jobRecords(self):
        qrycount=0 ; jobset = []
        for salary in self.salaryLevels:
            for search in self.categories:
                qryjobs = self.jobRecords_query(salary, search)
                jobset.append(qryjobs)
        jobs = pd.concat(jobset)
        #post new jobs to csv file
        if not jobs is None:
            jobs.to_csv(self.jobs['filename'],index=False)

            #update database with new jobs
            if self.jobs['records'] is None:
                self.jobs['records'] = jobs
            else:
                self.jobs['records'] = self.jobs['records'].append(jobs)
                self.jobs['records'].drop_duplicates(subset=['jobid'],inplace=True)
                self.jobs['records'].reset_index(inplace=True)
                del self.jobs['records']['index']
            database.add_jobs(self.jobs['records'],append=False)