from sqlalchemy import create_engine
import pandas as pd
import agent
import sqlite3
import gsheet.api as gs

engine = None
gs_engine = None
SQL_DB_NAME = 'sqlite:///jobs.db'
GSHEET_CONFIG = {'wkbid':'1JiB-ofvyimIOZ9vVxF22xIyXybIP5FCyo6N_x-pvmCs',
                   }

table_names = [
    'source',
    'job',
    'match',
]

sources = [
    {'name':'MyCareerFutures','url':'https://www.mycareersfuture.sg/'},
]

#sqlite db

def load(loadsheet=True):
    global engine, SQL_DB_NAME
    if engine is None:
        engine = create_engine(SQL_DB_NAME, echo=False)
    if loadsheet:
        load_gsheet()

def setup():
    'this script is used to initialize the database for the first time'
    global sources, engine
    # add sources
    s = pd.DataFrame(sources)
    s.to_sql('source', con=engine, if_exists='replace', index=False)
    # add jobs
    jobs = pd.read_csv(agent.files['job_openings'])
    add_jobs(jobs,append=False)

def add_jobs(jobs,append=True):
    global engine
    if append:
        ifex = 'append'
    else:
        ifex = 'replace'
    jobs.to_sql('job', con=engine, if_exists=ifex, index=False)

def get_sources():
    global engine
    s = pd.read_sql_table('source',con=engine)
    return s

def get_jobs():
    global engine
    jobs = pd.read_sql_table('job',con=engine)
    return jobs

def get_tags():
    tags = pd.read_sql_table('tag',con=engine)
    return tags

#gsheet

def load_gsheet():
    global gs_engine
    if gs_engine is None:
        gs_engine = gs.SheetsEngine()

def post_jobs_to_gsheet(jobs):
    wkbid = GSHEET_CONFIG['wkbid']
    rngid = 'openings!B2:H'

    #values is a 2D list [[]]
    values = jobs.values.astype('str').tolist()
    gs_engine.clear_rangevalues(wkbid,rngid)
    #write values - this method writes everything as a string
    gs_engine.set_rangevalues(wkbid,rngid,values)

def update_tags():
    wkbid = GSHEET_CONFIG['wkbid']
    rngid = 'tags!A2:D'
    taglist = gs_engine.get_rangevalues(wkbid,rngid)
    tags = pd.DataFrame(taglist, columns=['tag', 'tag_type','match_yn','score'])
    tags.to_sql('tag',con=engine,if_exists='replace',index=False)