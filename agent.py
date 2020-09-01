from selenium import webdriver
import bs4
import pandas as pd
import re
import numpy as np

import os
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
import datetime as dt
from timeit import default_timer as timer
import time

chrome_options = Options()
chrome_options.add_argument("--headless")
#chrome_options.binary_location = '/Applications/Google Chrome

class JobSearchWebsite(object):
    report_folder = ''
    data = None
    report = None
    driver = None
    pageSoup = None
    name = ''
    mainURL = 'https://'
    parserStr = "html5lib"
    resultElementTag = 'span'
    resultTag = 'search-results'
    resultMarkers = ['<div data-cy="search-result-headers">', 'jobs found based on your filters']
    cardTag = 'job-card-'
    jobs = {'records':None,'filename':'jobopenings.csv'}
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
                 search_defaults={'sort': 'new_posting_date', 'page': 0}, load_driver=True):
        self.name = name
        self.mainURL = mainURL
        self.searchFields = searchFields
        self.search_defaults = search_defaults
        if load_driver:
            self.loadDriver()
        if os.path.exists(self.jobs['filename']):
            self.jobs['records'] = pd.read_csv(self.jobs['filename'])

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
        for cat in self.categories:
            for salary in self.salaryLevels:
                checkpoint = timer()
                #          date ,     source, location,         emp type, category, salary, matching jobs, jobs total
                qryResult = self.jobsearchQuery(salary, cat, self.employmentType)
                queryJobs = qryResult['query jobs']
                totalJobs = qryResult['total jobs']
                rcdRow = [report_date, self.name, self.location, self.employmentType, cat, salary, queryJobs, totalJobs]
                data.append(rcdRow)
            print('query complete for job %s in %.2f seconds' % (cat, timer() - checkpoint))
        # create pandas dataframe for job search records and export to csv
        self.data = pd.DataFrame.from_records(data, columns=self.reportFields)
        self.data.to_csv(self.report_folder + '\\jobsearchdata.csv')

        # create pandas pivot table report from job search data and export to csv
        self.report = pd.pivot_table(self.data, index='job category', columns='monthly salary',
                                     values=['matching jobs'])
        self.report.to_csv(self.report_folder + '\\jobsearchreport.csv')
        print('job report complete in %.2f min' % (1 / 60 * (timer() - report_start)))

    def jobsearchQuery(self, salary=1000, category='Professional Services', employmentType='Full Time'):
        qryURL = self.jobsearch_URLquery(salary, category, employmentType, page=self.search_defaults['page'])
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

    def jobsearch_URLquery(self, salary, category, employmentType, page=0):
        filters = {}
        filters['salary'] = salary;
        filters['employmentType'] = employmentType;
        filters['category'] = category
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
        strPairs = [x.strip().replace(',', '') for x in resultStr.split('of')]
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
                    jobid = get_jobid(cardObj)
                    print('jobid: %s, original: %s, left filter: %s' % (jobid,postedStr, daysStr_1))

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

        # job id
        def get_jobid(cardObj):
            url_keyword = 'JobCard__card'  # unique tag identifier
            urlA = [y for y in cardObj.find_all('a') if url_keyword in str(y)][0]
            leftbloc = 'href="/job/'
            rightbloc = '"><div class="w-80-l w-100 flex flex-wrap'
            prjidStr = re.search(leftbloc + '(.*)' + rightbloc, str(urlA)).group(1)
            return prjidStr

        jobRecord = {}
        jobRecord['salaryHigh'] = get_salaryHigh(cardObj)
        jobRecord['position_title'] = get_position_title(cardObj)
        jobRecord['posted_date'] = get_posted_date(cardObj)
        jobRecord['company_name'] = get_company_name(cardObj)
        jobRecord['jobid'] = get_jobid(cardObj)
        return jobRecord

    def jobRecords_query(self,salary, category, employmentType):
        cardcount = 1; page = 0
        while cardcount > 0:
            qryURL = self.jobsearch_URLquery(salary, category, employmentType, page)
            self.refresh_pageSoup(qryURL)

            # list of cards using the tag 'job-card-'
            cards = [y for y in [x for x in self.pageSoup.find_all('div')
                                 if x.has_attr('id')] if self.cardTag in y['id']]
            cardcount = len(cards)
            if cardcount > 0:
                # create DataFrame object from card objects
                if page == 0:
                    jobs = pd.DataFrame.from_records([self.get_jobRecord_fromcard(x) for x in cards])
                else:
                    morejobs = pd.DataFrame.from_records([self.get_jobRecord_fromcard(x) for x in cards])
                    jobs = jobs.append(morejobs)
            page = page + 1

        return jobs

    def update_jobRecords(self):
        qrycount=0
        for salary in self.salaryLevels:
            for cat in self.categories:
                if qrycount == 0:
                    jobs = self.jobRecords_query(salary, cat, self.employmentType)
                else:
                    morejobs = self.jobRecords_query(salary, cat, self.employmentType)
                    jobs = jobs.append(morejobs)
                qrycount = qrycount +1

        if self.jobs['records'] is None:
            self.jobs['records'] = jobs
        else:
            self.jobs['records'] = self.jobs['records'].append(jobs)
            self.jobs['records'].drop_duplicates(subset=['jobid'],inplace=True)
            self.jobs['records'].reset_index(inplace=True)
            del self.jobs['records']['index']
        self.jobs['records'].to_csv(self.jobs['filename'],index=False)
