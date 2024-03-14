import os
from datetime import datetime
import logging
logger = logging.getLogger(__name__)
import yaml
import sqlite3
from .routine import Routine
from .settings import read_value
from .utils import get_yaml_string
from .errors import BadgerConfigError, BadgerDBError


# Check badger database root
BADGER_DB_ROOT = read_value('BADGER_DB_ROOT')
if BADGER_DB_ROOT is None:
    raise BadgerConfigError('Please set the BADGER_DB_ROOT env var!')
elif not os.path.exists(BADGER_DB_ROOT):
    os.makedirs(BADGER_DB_ROOT)
    logger.info(
        f'Badger database root {BADGER_DB_ROOT} created')


def maybe_create_routines_db(func):

    def func_safe(*args, **kwargs):
        db_routine = os.path.join(BADGER_DB_ROOT, 'routines.db')

        con = sqlite3.connect(db_routine)
        cur = con.cursor()

        cur.execute('create table if not exists routine (name not null primary key, config, savedAt timestamp)')

        con.commit()
        con.close()

        return func(*args, **kwargs)

    return func_safe


def maybe_create_runs_db(func):

    def func_safe(*args, **kwargs):
        db_run = os.path.join(BADGER_DB_ROOT, 'runs.db')

        con = sqlite3.connect(db_run)
        cur = con.cursor()

        cur.execute('create table if not exists run (id integer primary key, savedAt timestamp, finishedAt timestamp, routine, filename)')

        con.commit()
        con.close()

        return func(*args, **kwargs)

    return func_safe


def filter_routines(records, tags):
    records_filtered = []
    for record in records:
        try:
            _tags = yaml.safe_load(record[1])['config']['tags']
            if tags.items() <= _tags.items():
                records_filtered.append(record)
        except:
            pass

    return records_filtered


def extract_descriptions(records):
    descr_list = []
    for record in records:
        try:
            descr = yaml.safe_load(record[1])['description']
            descr_list.append(descr)
        except Exception:
            descr_list.append('')

    return descr_list


@maybe_create_routines_db
def save_routine(routine: Routine):
    db_routine = os.path.join(BADGER_DB_ROOT, 'routines.db')

    con = sqlite3.connect(db_routine)
    cur = con.cursor()

    cur.execute('select * from routine where name=:name',
                {'name': routine.name})
    record = cur.fetchone()

    runs = get_runs_by_routine(routine.name)

    if record and len(runs) == 0:  # update the record
        cur.execute('update routine set config = ?, savedAt = ? where name = ?',
                    (routine.yaml(), datetime.now(), routine.name))
    else:  # insert a record
        cur.execute('insert into routine values (?, ?, ?)',
                    (routine.name, routine.yaml(), datetime.now()))

    con.commit()
    con.close()


# This function is not safe and might break database! Use with caution!
@maybe_create_routines_db
def update_routine(routine: Routine):
    db_routine = os.path.join(BADGER_DB_ROOT, 'routines.db')

    con = sqlite3.connect(db_routine)
    cur = con.cursor()

    cur.execute('select * from routine where name=:name',
                {'name': routine.name})
    record = cur.fetchone()

    if record:  # update the record
        cur.execute('update routine set config = ?, savedAt = ? where name = ?',
                    (routine.yaml(), datetime.now(), routine.name))

    con.commit()
    con.close()


@maybe_create_routines_db
@maybe_create_runs_db
def remove_routine(name, remove_runs=False):
    db_routine = os.path.join(BADGER_DB_ROOT, 'routines.db')

    con = sqlite3.connect(db_routine)
    cur = con.cursor()

    cur.execute(f'delete from routine where name = "{name}"')

    con.commit()
    con.close()

    if remove_runs:
        # Remove all related run records
        db_run = os.path.join(BADGER_DB_ROOT, 'runs.db')

        con = sqlite3.connect(db_run)
        cur = con.cursor()

        cur.execute(f'delete from run where routine = "{name}"')

        con.commit()
        con.close()


@maybe_create_routines_db
def load_routine(name: str):
    db_routine = os.path.join(BADGER_DB_ROOT, 'routines.db')
    con = sqlite3.connect(db_routine)
    cur = con.cursor()

    cur.execute('select * from routine where name=:name', {'name': name})

    records = cur.fetchall()
    con.close()

    if len(records) == 1:
        # return yaml.safe_load(records[0][1]), records[0][2]
        routine_dict = yaml.safe_load(records[0][1])
        # routine_dict['evaluator'] = None
        return Routine(**routine_dict), records[0][2]
    elif len(records) == 0:
        # logger.warning(f'Routine {name} not found in the database!')
        return None, None
    else:
        raise BadgerDBError(
            f'Multiple routines with name {name} found in the database!')


@maybe_create_routines_db
def list_routine(keyword='', tags={}):
    db_routine = os.path.join(BADGER_DB_ROOT, 'routines.db')
    con = sqlite3.connect(db_routine)
    cur = con.cursor()

    cur.execute(f'select name, config, savedAt from routine where name like "%{keyword}%" order by savedAt desc')
    records = cur.fetchall()
    if tags:
        records = filter_routines(records, tags)
    names = [record[0] for record in records]
    timestamps = [record[2] for record in records]
    descriptions = extract_descriptions(records)
    con.close()

    return names, timestamps, descriptions


@maybe_create_runs_db
def save_run(run):
    db_run = os.path.join(BADGER_DB_ROOT, 'runs.db')

    con = sqlite3.connect(db_run)
    cur = con.cursor()

    # Insert or update a record
    routine_name = run['routine'].name
    run_filename = run['filename']
    timestamps = run['data']['timestamp']
    time_start = datetime.fromtimestamp(timestamps[0])
    time_finish = datetime.fromtimestamp(timestamps[-1])

    # Check if the record exist (same filename)
    cur.execute('select id from run where filename = ?', (run_filename,))
    existing_row = cur.fetchone()

    if existing_row:
        cur.execute('update run set finishedAt = ? where filename = ?',
                    (time_finish, run_filename))
        rid = existing_row[0]
    else:
        cur.execute('insert into run values (?, ?, ?, ?, ?)',
                    (None, time_start, time_finish, routine_name, run_filename))
        rid = cur.lastrowid

    con.commit()
    con.close()

    return rid


@maybe_create_runs_db
def get_runs_by_routine(routine: str):
    db_run = os.path.join(BADGER_DB_ROOT, 'runs.db')

    con = sqlite3.connect(db_run)
    cur = con.cursor()

    cur.execute(f'select filename from run where routine = "{routine}" order by savedAt desc')
    records = cur.fetchall()
    con.close()

    filenames = [record[0] for record in records]

    return filenames


@maybe_create_runs_db
def get_runs():
    db_run = os.path.join(BADGER_DB_ROOT, 'runs.db')

    con = sqlite3.connect(db_run)
    cur = con.cursor()

    cur.execute(f'select filename from run order by savedAt desc')
    records = cur.fetchall()

    con.close()

    filenames = [record[0] for record in records]

    return filenames


@maybe_create_runs_db
def remove_run_by_filename(name):
    db_run = os.path.join(BADGER_DB_ROOT, 'runs.db')

    con = sqlite3.connect(db_run)
    cur = con.cursor()

    cur.execute(f'delete from run where filename = "{name}"')

    con.commit()
    con.close()


@maybe_create_runs_db
def remove_run_by_id(rid):
    db_run = os.path.join(BADGER_DB_ROOT, 'runs.db')

    con = sqlite3.connect(db_run)
    cur = con.cursor()

    cur.execute(f'delete from run where id = {rid}')

    con.commit()
    con.close()


def import_routines(filename):
    con = sqlite3.connect(filename)
    cur = con.cursor()

    # Deal with empty db file
    cur.execute('create table if not exists routine (name not null primary key, config, savedAt timestamp)')

    db_routine = os.path.join(BADGER_DB_ROOT, 'routines.db')
    con_db = sqlite3.connect(db_routine)
    cur_db = con_db.cursor()

    cur.execute('select * from routine')
    records = cur.fetchall()

    failed_list = []
    for record in records:
        try:
            cur_db.execute('insert into routine values (?, ?, ?)', record)
        except:
            failed_list.append(record[0])

    con_db.commit()
    con_db.close()

    con.close()

    if failed_list:
        raise BadgerDBError(get_yaml_string(failed_list))


def export_routines(filename, routine_name_list):
    con = sqlite3.connect(filename)
    cur = con.cursor()

    cur.execute('create table if not exists routine (name not null primary key, config, savedAt timestamp)')

    db_routine = os.path.join(BADGER_DB_ROOT, 'routines.db')
    con_db = sqlite3.connect(db_routine)
    cur_db = con_db.cursor()

    for name in routine_name_list:
        cur_db.execute('select * from routine where name=:name', {'name': name})
        records = cur_db.fetchall()
        record = records[0]  # should only have one hit

        cur.execute('insert into routine values (?, ?, ?)', record)

    con_db.close()

    con.commit()
    con.close()
