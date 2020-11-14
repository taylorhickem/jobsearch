from sqlalchemy import create_engine
from sqlalchemy.engine.reflection import Inspector
import pandas as pd
import agent
import sqlite3
import gsheet.api as gs

engine = None
inspector = None
gs_engine = None
SQL_DB_NAME = 'sqlite:///jobs.db'
GSHEET_CONFIG = {'wkbid':'1JiB-ofvyimIOZ9vVxF22xIyXybIP5FCyo6N_x-pvmCs',
                 'openings':'openings!A2:H',
                 'screened':'screened!A2:I',
                 'tags':'tags!A2:D',
                   }

table_names = []

sources = [
    {'name':'MyCareerFutures','url':'https://www.mycareersfuture.sg/'},
]

#sqlite db

def load(loadsheet=True):
    global engine, SQL_DB_NAME, table_names
    if engine is None:
        engine = create_engine(SQL_DB_NAME, echo=False)
        load_inspector()

    if loadsheet:
        load_gsheet()

def load_inspector():
    global inspector, table_names
    inspector = Inspector.from_engine(engine)
    table_names = inspector.get_table_names()

def setup():
    'this script is used to initialize the database for the first time'
    global sources, engine
    # add sources
    s = pd.DataFrame(sources)
    s.to_sql('source', con=engine, if_exists='replace', index=False)
    # add jobs
    jobs = pd.read_csv(agent.files['job_openings'])
    add_jobs(jobs,append=False)

def table_exists(tableName):
    global inspector, table_names
    load_inspector()
    return tableName in table_names

def update_table(tbl,tblname,append=True):
    global engine
    if append:
        ifex = 'append'
    else:
        ifex = 'replace'
    tbl.to_sql(tblname, con=engine, if_exists=ifex, index=False)

def add_jobs(jobs,append=True):
    global engine
    if append:
        ifex = 'append'
    else:
        ifex = 'replace'
    jobs.to_sql('job', con=engine, if_exists=ifex, index=False)

def update_match(new_matches,update=True):
    global engine
    match = get_table('match')
    if match is None:
        match = new_matches
    else:
        new_matches.set_index('jobid',inplace=True)
        match.set_index('jobid',inplace=True)
        match.update(new_matches)
        match.reset_index(inplace=True)
    match.to_sql('match', con=engine, if_exists='replace', index=False)

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

def get_table(tableName):
    if table_exists(tableName):
        tbl = pd.read_sql_table(tableName,con=engine)
    else:
        tbl = None
    return tbl

#gsheet

def load_gsheet():
    global gs_engine
    if gs_engine is None:
        gs_engine = gs.SheetsEngine()

def post_to_gsheet(df,rng_code):
    #values is a 2D list [[]]
    wkbid = GSHEET_CONFIG['wkbid']
    rngid = GSHEET_CONFIG[rng_code]
    values = df.values.astype('str').tolist()
    gs_engine.clear_rangevalues(wkbid,rngid)
    #write values - this method writes everything as a string
    gs_engine.set_rangevalues(wkbid,rngid,values)

def post_jobs_to_gsheet(df):
    post_to_gsheet(df,'openings')

def update_tags():
    wkbid = GSHEET_CONFIG['wkbid']
    rngid = GSHEET_CONFIG['tags']
    taglist = gs_engine.get_rangevalues(wkbid,rngid)
    tags = pd.DataFrame(taglist, columns=['tag', 'tag_type','group','score'])
    tags.to_sql('tag',con=engine,if_exists='replace',index=False)