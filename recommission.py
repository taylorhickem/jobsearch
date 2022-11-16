'''this module is a guide to use for recommissioning the app after an extended period of dormancy
the purpose of recommissioning is to update the scraper for changes in the
page source of the target sites as well as the web driver version
'''

#----------------------------------------------------------------------
#01 update web driver
#----------------------------------------------------------------------
# the first step is the update the web driver to the latest version
# see the wiki for detailed instructions and link to the Chrome webdriver download page
# git_repo_url/wiki/Chrome-webdriver-version-update

#----------------------------------------------------------------------
#-- Setup test workspace
#----------------------------------------------------------------------
import json
import report
import mcf_profile

jobsite = None
CASE = {}
TESTS = {}
DATE_FORMAT = '%Y-%m-%d'


def run_tests():
    global TESTS
    test_result = {
        'success': False,
        'message': 'Failed'
    }
    test_success = t001_load_agent()
    if test_success:
        test_success = t002_load_sourcecode()
    if test_success:
        test_success = t003_get_jobcards()
    if test_success:
        test_success = t004_read_jobcard()
    if test_success:
        test_success = t005a_load_new_job_profile()
    #if test_success:
    #    test_success = t005b_load_job_profile()
    if test_success:
        test_success = t006_screen_jobs()

    if test_success:
        test_result['success'] = True
        test_result['message'] = 'all tests passed'

    TESTS['tests_result'] = test_result
    print('tests result, success: %s, %s' % (
        test_result['success'],
        test_result['message']
    ))
    log_results()


def log_results():
    global TESTS
    with open('test_result.json', 'w') as f:
        json.dump(TESTS, f)

#----------------------------------------------------------------------
#01 load the jobsite
#----------------------------------------------------------------------
def t001_load_agent():
    global TESTS, jobsite

    test_name = 't001_load_agent'
    test_result = {
        "success": False,
        "message": "Failed"
    }

    if jobsite is None:
        try:
            report.load()
            jobsite = report.jobsite
            test_result['success'] = True
            test_result['message'] = 'loaded agent'
        except Exception as e:
            test_result['message'] = str(e)
            if jobsite is not None:
                jobsite = None

    TESTS[test_name] = test_result
    print('test result: %s, success: %s, %s' % (
        test_name,
        test_result['success'],
        test_result['message']
    ))
    return test_result['success']

#----------------------------------------------------------------------
#02 load source code using chrome driver
#----------------------------------------------------------------------
def t002_load_sourcecode():
    global TESTS, CASE, jobsite

    test_name = 't002_load_sourcecode'
    test_result = {
        "success": False,
        "message": "Failed"
    }

    search_config = report.SEARCH_CONFIG['search']
    keywords = search_config['keywords']
    salary_min = search_config['salary_min']
    keyword0 = keywords[0]
    page0 = 0

    if jobsite is not None:
        try:
            jobsite.set_report_parameters([salary_min], keywords)
            qryURL = jobsite.jobsearch_URLquery(salary_min, keyword0, page0)
            jobsite.refresh_pageSoup(qryURL)

            test_result['success'] = True
            test_result['message'] = 'loaded source code'
        except Exception as e:
            test_result['message'] = str(e)
            jobsite.driver.quit()

    CASE['search_config'] = search_config
    CASE['keyword'] = keyword0
    CASE['salary_min'] = salary_min

    TESTS['search_config'] = search_config
    TESTS['keyword'] = keyword0
    TESTS['salary_min'] = salary_min
    TESTS[test_name] = test_result
    print('test result: %s, success: %s, %s' % (
        test_name,
        test_result['success'],
        test_result['message']
    ))
    return test_result['success']


#----------------------------------------------------------------------
#03 jobcards
#----------------------------------------------------------------------
def t003_get_jobcards():
    global TESTS, CASE, jobsite

    test_name = 't003_get_jobcards'
    test_result = {
        "success": False,
        "message": "Failed"
    }
    cards = []

    if jobsite is not None:
        try:
            cards = [y for y in [x for x in jobsite.pageSoup.find_all('div')
                                 if x.has_attr('id')] if jobsite.cardTag in y['id']]
            cardcount = len(cards)
            if cardcount > 0:
                test_result['success'] = True
                test_result['message'] = 'loaded cards from source code'
            else:
                test_result['message'] = 'could not find any job cards'
        except Exception as e:
            test_result['message'] = str(e)
            jobsite.driver.quit()

    CASE['job_cards'] = cards
    TESTS[test_name] = test_result
    print('test result: %s, success: %s, %s' % (
        test_name,
        test_result['success'],
        test_result['message']
    ))
    return test_result['success']


#----------------------------------------------------------------------
#04 html tag logic: jobcard
#----------------------------------------------------------------------
def t004_read_jobcard():
    global TESTS, CASE, jobsite

    test_name = 't004_read_jobcard'
    test_result = {
        "success": False,
        "message": "Failed"
    }
    rcd = {}
    cards = CASE['job_cards']
    card0 = cards[0]

    if len(cards) > 0:
        try:
            rcd = jobsite.get_jobRecord_fromcard(card0)
            test_result['success'] = True
            test_result['message'] = json.dumps(rcd)
        except Exception as e:
            test_result['message'] = str(e)
            jobsite.driver.quit()

    CASE['job_card'] = card0
    CASE['job_card_record'] = rcd
    TESTS['job_card_record'] = rcd
    TESTS[test_name] = test_result
    print('test result: %s, success: %s, %s' % (
        test_name,
        test_result['success'],
        test_result['message']
    ))
    return test_result['success']


#----------------------------------------------------------------------
#05 load job profiles
#----------------------------------------------------------------------
def t005a_load_new_job_profile():
    global TESTS, CASE, jobsite

    test_name = 't005a_load_new_job_profile'
    test_result = {
        "success": False,
        "message": "Failed"
    }
    rcd = {}

    mcf_profile.jobsite = jobsite
    mainURL = jobsite.mainURL
    mcf_profile.mainURL = mainURL
    urlid = CASE['job_card_record']['urlid']
    jobid = CASE['job_card_record']['jobid']

    try:
        rcd = mcf_profile.get_profileRecord(urlid, jobid, mainURL)
        rcd['closing_date'] = rcd['closing_date'].strftime(DATE_FORMAT)
        rcd['description'] = rcd['description'][:100]
        test_result['success'] = True
        test_result['message'] = json.dumps(rcd)
    except Exception as e:
        test_result['message'] = str(e)
        jobsite.driver.quit()

    CASE['new_jobid'] = jobid
    CASE['new_profile_record'] = rcd

    TESTS['new_jobid'] = jobid
    TESTS['new_profile_record'] = rcd
    TESTS[test_name] = test_result
    print('test result: %s, success: %s, %s' % (
        test_name,
        test_result['success'],
        test_result['message']
    ))
    return test_result['success']


def t005b_load_job_profile():
    global TESTS, CASE, jobsite

    test_name = 't005b_load_job_profile'
    test_result = {
        "success": False,
        "message": "Failed"
    }
    rcd = {}

    mcf_profile.jobsite = jobsite
    mainURL = jobsite.mainURL
    mcf_profile.mainURL = mainURL

    try:
        mcf_profile.db.load()
        jobids = mcf_profile.get_profile_ids()
        if jobids is not None:
            idList = jobids.values.tolist()
            id_tuple0 = idList[0]
            urlid0 = id_tuple0[1]
            jobid0 = id_tuple0[0]
            rcd = mcf_profile.get_profileRecord(urlid0, jobid0, mainURL)
            rcd['closing_date'] = rcd['closing_date'].strftime(DATE_FORMAT)
            rcd['description'] = rcd['description'][:100]
            test_result['success'] = True
            test_result['message'] = json.dumps(rcd)
        else:
            test_result['message'] = 'failed to load jobids'
    except Exception as e:
        test_result['message'] = str(e)
        jobsite.driver.quit()

    CASE['jobid'] = jobid0
    CASE['profile_record'] = rcd

    TESTS['jobid'] = jobid0
    TESTS['profile_record'] = rcd
    TESTS[test_name] = test_result
    print('test result: %s, success: %s, %s' % (
        test_name,
        test_result['success'],
        test_result['message']
    ))
    return test_result['success']

#----------------------------------------------------------------------
#06 screen_jobs
#----------------------------------------------------------------------
def t006_screen_jobs():
    global TESTS, jobsite

    test_name = 't006_screen_jobs'
    test_result = {
        "success": False,
        "message": "Failed"
    }

    try:
        report.screen_jobs()
        test_result['success'] = True
        test_result['message'] = 'screened jobs'
    except Exception as e:
        test_result['message'] = str(e)
        jobsite.driver.quit()

    TESTS[test_name] = test_result
    print('test result: %s, success: %s, %s' % (
        test_name,
        test_result['success'],
        test_result['message']
    ))
    return test_result['success']


if __name__ == '__main__':
    run_tests()