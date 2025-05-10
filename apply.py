""" automate applications through MyCareerFutures website
process steps
1. login google sheets download list of jobs to apply
       - identify the job track
       - identify the CV to apply associated with the job track
2. connect to existing authenticated session, or exit and return error message
3. apply to jobs
       load job url
       find and submit the apply button
       find and select the CV
       page through the 1-click application pages
       exit if run into a questionnaire
 """

# dependencies -----------------------------------------------
import agent


# constants -----------------------------------------------
MCF_WEBSITE = 'https://www.mycareersfuture.gov.sg/'


# main -----------------------------------------------------
