from selenium import webdriver
import bs4
import pandas as pd
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
    jobcardlistMarker = 'card-list'
    jobcardMarker = 'job-card-'
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

    def get_jobcards_bypage(self, qryURL, page=0):
        # returns a list of soup tags objects
        newURL = qryURL.replace(qryURL[qryURL.find('&page='):], '&page=' + str(page))
        self.refresh_pageSoup(newURL)
        cardlist = self.pageSoup.findAll('div', {'class': self.jobcardlistMarker})
        cards = [cardlist[0].findAll('div', {'id': self.jobcardMarker + str(i)})[0] for i in range(self.cardsPerPage)]
        return cards