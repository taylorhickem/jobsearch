from sqlalchemy import create_engine
import pandas as pd
import agent
import sqlite3

engine = None
SQL_DB_NAME = 'sqlite:///jobs.db'

table_names = [
    'source',
    'job',
    'match',
]

sources = [
    {'name':'MyCareerFutures','url':'https://www.mycareersfuture.sg/'},
]

def load():
    global engine, SQL_DB_NAME
    if engine is None:
        engine = create_engine(SQL_DB_NAME, echo=False)

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