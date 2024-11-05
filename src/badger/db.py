import os
import warnings
from datetime import datetime
import logging

import yaml
import sqlite3
import uuid

from badger.routine import Routine
from badger.settings import init_settings
from badger.utils import get_yaml_string
from badger.errors import BadgerConfigError, BadgerDBError

logger = logging.getLogger(__name__)

# Check badger database root
config_singleton = init_settings()
BADGER_DB_ROOT = config_singleton.read_value("BADGER_DB_ROOT")
if BADGER_DB_ROOT is None:
    raise BadgerConfigError("Please set the BADGER_DB_ROOT env var!")
elif not os.path.exists(BADGER_DB_ROOT):
    os.makedirs(BADGER_DB_ROOT)
    logger.info(f"Badger database root {BADGER_DB_ROOT} created")


def ensure_routines_db_exists(func):
    """
    Create the routines database (a SQL table) if it does not already exist.
    """

    def func_safe(*args, **kwargs):
        db_routine = os.path.join(BADGER_DB_ROOT, "routines.db")

        con = sqlite3.connect(db_routine)
        cur = con.cursor()

        cur.execute(
            "create table if not exists routine (id text primary key, name text, config, savedAt timestamp)"
        )

        con.commit()
        con.close()

        return func(*args, **kwargs)

    return func_safe


def ensure_runs_db_exists(func):
    """
    Create the runs database (a SQL table) if it does not already exist.
    """

    def func_safe(*args, **kwargs):
        db_run = os.path.join(BADGER_DB_ROOT, "runs.db")

        con = sqlite3.connect(db_run)
        cur = con.cursor()

        cur.execute(
            "create table if not exists run (id integer primary key, savedAt timestamp, finishedAt timestamp, routine_id, filename)"
        )

        con.commit()
        con.close()

        return func(*args, **kwargs)

    return func_safe


def filter_routines(records, tags):
    records_filtered = []
    for record in records:
        try:
            _tags = yaml.safe_load(record[3])["config"]["tags"]
            if tags.items() <= _tags.items():
                records_filtered.append(record)
        except:
            pass

    return records_filtered


def extract_metadata(records):
    env_list = []
    descr_list = []
    for record in records:
        try:
            metadata = yaml.safe_load(record[2])
            env = metadata["environment"]["name"]
            env_list.append(env)
            descr = metadata["description"]
            descr_list.append(descr)
        except Exception:
            env_list.append("")
            descr_list.append("")

    return env_list, descr_list


@ensure_routines_db_exists
def save_routine(routine: Routine):
    db_routine = os.path.join(BADGER_DB_ROOT, "routines.db")

    con = sqlite3.connect(db_routine)
    cur = con.cursor()

    id = str(uuid.uuid4())
    routine.id = id
    cur.execute(
        "insert into routine values (?, ?, ?, ?)",
        (routine.id, routine.name, routine.yaml(), datetime.now()),
    )

    con.commit()
    con.close()


# This function is not safe and might break database! Use with caution!
@ensure_routines_db_exists
def update_routine(routine: Routine):
    db_routine = os.path.join(BADGER_DB_ROOT, "routines.db")

    con = sqlite3.connect(db_routine)
    cur = con.cursor()

    cur.execute("select * from routine where id=:id", {"id": routine.id})
    record = cur.fetchone()

    if record:  # update the record
        cur.execute(
            "update routine set name = ?, config = ?, savedAt = ? where id = ?",
            (routine.name, routine.yaml(), datetime.now(), routine.id),
        )

    con.commit()
    con.close()


@ensure_routines_db_exists
@ensure_runs_db_exists
def remove_routine(id: str, remove_runs=True):
    db_routine = os.path.join(BADGER_DB_ROOT, "routines.db")

    con = sqlite3.connect(db_routine)
    cur = con.cursor()

    cur.execute(f'delete from routine where id = "{id}"')

    con.commit()
    con.close()

    if remove_runs:
        # Remove all related run records
        db_run = os.path.join(BADGER_DB_ROOT, "runs.db")

        con = sqlite3.connect(db_run)
        cur = con.cursor()

        cur.execute(f'delete from run where routine_id = "{id}"')

        con.commit()
        con.close()


@ensure_routines_db_exists
def load_routine(id: str):
    db_routine = os.path.join(BADGER_DB_ROOT, "routines.db")
    con = sqlite3.connect(db_routine)
    cur = con.cursor()

    if isinstance(id, str) and id.strip():
        cur.execute("select * from routine where id=:id", {"id": id})
    else:
        raise ValueError("Expected id to be a non-empty string.")

    records = cur.fetchall()
    con.close()

    if len(records) == 1:
        # return yaml.safe_load(records[0][1]), records[0][2]
        routine_dict = yaml.safe_load(records[0][2])
        # routine_dict['evaluator'] = None
        with warnings.catch_warnings(record=True) as caught_warnings:
            routine = Routine(**routine_dict)

            # Check if any user warnings were caught
            for warning in caught_warnings:
                if isinstance(warning.category, UserWarning):
                    pass
                else:
                    print(f"Caught user warning: {warning.message}")

            return routine, records[0][3]
    elif len(records) == 0:
        raise BadgerDBError(f"Routine id {id} not found in the database!")
    else:
        raise BadgerDBError(f"Multiple routines with id {id} found in the database!")


@ensure_routines_db_exists
def list_routine(keyword="", tags={}):
    db_routine = os.path.join(BADGER_DB_ROOT, "routines.db")
    con = sqlite3.connect(db_routine)
    cur = con.cursor()

    # check if id column is in database
    # if not, add it and update routine and run entries accordingly
    cur.execute("pragma table_info(routine)")
    columns = [row[1] for row in cur.fetchall()]
    if "id" not in columns:
        cur.execute("""
        create table new_table (
            id text primary key,
            name text,
            config,
            savedAt timestamp
        )
        """)
        db_run = os.path.join(BADGER_DB_ROOT, "runs.db")
        con_run = sqlite3.connect(db_run)
        cur_run = con_run.cursor()
        cur_run.execute("alter table run rename column routine to routine_id")
        con_run.commit()
        con_run.close()
        cur.execute("select * from routine")
        rows = cur.fetchall()
        for row in rows:
            id = str(uuid.uuid4())
            config = yaml.safe_load(row[1])
            config["id"] = id
            sorted_config = dict(sorted(config.items()))
            new_config = yaml.dump(sorted_config, default_flow_style=False)
            cur.execute(
                "insert into new_table (id, name, config, savedAt) values (?, ?, ?, ?)",
                (id, row[0], new_config, row[2]),
            )
            db_run = os.path.join(BADGER_DB_ROOT, "runs.db")
            con_run = sqlite3.connect(db_run)
            cur_run = con_run.cursor()
            # now the column in run table is called 'routine_id' but they are still routine names
            cur_run.execute(
                "update run set routine_id = ? where routine_id = ?", (id, row[0])
            )
            con_run.commit()
            con_run.close()
            filenames = get_runs_by_routine(id)
            # Check badger optimization run archive root
            config_singleton = init_settings()
            BADGER_ARCHIVE_ROOT = config_singleton.read_value("BADGER_ARCHIVE_ROOT")
            if BADGER_ARCHIVE_ROOT is None:
                raise BadgerConfigError("Please set the BADGER_ARCHIVE_ROOT env var!")
            elif not os.path.exists(BADGER_ARCHIVE_ROOT):
                os.makedirs(BADGER_ARCHIVE_ROOT)
                logger.info(f"Badger run root {BADGER_ARCHIVE_ROOT} created")
            for i, fname in enumerate(filenames):
                tokens = fname.split("-")
                first_level = tokens[1]
                second_level = f"{tokens[1]}-{tokens[2]}"
                third_level = f"{tokens[1]}-{tokens[2]}-{tokens[3]}"

                filename = os.path.join(
                    BADGER_ARCHIVE_ROOT, first_level, second_level, third_level, fname
                )
                filenames[i] = filename
            for filename in filenames:
                with open(filename, "r") as file:
                    run = yaml.safe_load(file)
                run["id"] = id
                sorted_run = {key: run[key] for key in sorted(run.keys())}
                with open(filename, "w") as file:
                    yaml.dump(sorted_run, file, default_flow_style=False)
        cur.execute("drop table routine")
        cur.execute("alter table new_table rename to routine")
        con.commit()

    cur.execute(
        f"select id, name, config, savedAt from routine where name like '%{keyword}%' order by savedAt desc"
    )
    records = cur.fetchall()
    if tags:
        records = filter_routines(records, tags)
    ids = [record[0] for record in records]
    names = [record[1] for record in records]
    timestamps = [record[3] for record in records]
    environments, descriptions = extract_metadata(records)
    con.close()

    return ids, names, timestamps, environments, descriptions


@ensure_runs_db_exists
def save_run(run):
    db_run = os.path.join(BADGER_DB_ROOT, "runs.db")

    con = sqlite3.connect(db_run, timeout=30.0)
    cur = con.cursor()

    # Insert or update a record
    routine_id = run["routine"].id
    run_filename = run["filename"]
    timestamps = run["data"]["timestamp"]
    time_start = datetime.fromtimestamp(timestamps[0])
    time_finish = datetime.fromtimestamp(timestamps[-1])

    # Check if the record exist (same filename)
    cur.execute("select id from run where filename = ?", (run_filename,))
    existing_row = cur.fetchone()

    if existing_row:
        cur.execute(
            "update run set finishedAt = ? where filename = ?",
            (time_finish, run_filename),
        )
        rid = existing_row[0]
    else:
        cur.execute(
            "insert into run values (?, ?, ?, ?, ?)",
            (None, time_start, time_finish, routine_id, run_filename),
        )
        rid = cur.lastrowid

    con.commit()
    con.close()

    return rid


@ensure_runs_db_exists
def get_runs_by_routine(routine_id: str):
    db_run = os.path.join(BADGER_DB_ROOT, "runs.db")

    con = sqlite3.connect(db_run)
    cur = con.cursor()

    cur.execute(
        f'select filename from run where routine_id = "{routine_id}" order by savedAt desc'
    )
    records = cur.fetchall()
    con.close()

    filenames = [record[0] for record in records]

    return filenames


@ensure_runs_db_exists
def get_runs():
    db_run = os.path.join(BADGER_DB_ROOT, "runs.db")

    con = sqlite3.connect(db_run)
    cur = con.cursor()

    cur.execute("select filename from run order by savedAt desc")
    records = cur.fetchall()

    con.close()

    filenames = [record[0] for record in records]

    return filenames


@ensure_runs_db_exists
def remove_run_by_filename(filename):
    db_run = os.path.join(BADGER_DB_ROOT, "runs.db")

    con = sqlite3.connect(db_run)
    cur = con.cursor()

    cur.execute(f'delete from run where filename = "{filename}"')

    con.commit()
    con.close()


@ensure_runs_db_exists
def remove_run_by_id(rid):
    db_run = os.path.join(BADGER_DB_ROOT, "runs.db")

    con = sqlite3.connect(db_run)
    cur = con.cursor()

    cur.execute(f"delete from run where id = {rid}")

    con.commit()
    con.close()


def import_routines(filename):
    con = sqlite3.connect(filename)
    cur = con.cursor()

    # Deal with empty db file
    cur.execute(
        "create table if not exists routine (id text primary key, name text, config, savedAt timestamp)"
    )

    db_routine = os.path.join(BADGER_DB_ROOT, "routines.db")
    con_db = sqlite3.connect(db_routine)
    cur_db = con_db.cursor()

    cur.execute("select * from routine")
    records = cur.fetchall()

    failed_list = []
    for record in records:
        try:
            cur_db.execute("insert into routine values (?, ?, ?, ?)", record)
        except:
            failed_list.append(record[0])

    con_db.commit()
    con_db.close()

    con.close()

    if failed_list:
        raise BadgerDBError(get_yaml_string(failed_list))


def export_routines(filename, routine_id_list):
    con = sqlite3.connect(filename)
    cur = con.cursor()

    cur.execute(
        "create table if not exists routine (id text primary key, name text, config, savedAt timestamp)"
    )

    db_routine = os.path.join(BADGER_DB_ROOT, "routines.db")
    con_db = sqlite3.connect(db_routine)
    cur_db = con_db.cursor()

    for id in routine_id_list:
        cur_db.execute("select * from routine where id=:id", {"id": id})
        records = cur_db.fetchall()
        record = records[0]  # should only have one hit

        cur.execute("insert into routine values (?, ?, ?, ?)", record)

    con_db.close()

    con.commit()
    con.close()
