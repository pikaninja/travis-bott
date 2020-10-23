from os.path import isfile
from sqlite3 import connect

from apscheduler.triggers.cron import CronTrigger

DB_PATH = "./data/db/database.db"
BUILD_PATH = "./data/db/build.sql"

cxn = connect(DB_PATH, check_same_thread=False)
cur = cxn.cursor()


def with_commit(func):
    async def inner(*args, **kwargs):
        func(*args, **kwargs)
        await commit()

    return inner


@with_commit
async def build():
    if isfile(BUILD_PATH):
        await script_exec(BUILD_PATH)


async def commit():
    cxn.commit()


async def auto_save(schedule):
    schedule.add_job(commit, CronTrigger(second=0))


async def close():
    cxn.close()


async def field(command, *values):
    cur.execute(command, tuple(values))

    if (fetch := cur.fetchone()) is not None:
        return fetch[0]


def field_nonasync(command, *values):
    cur.execute(command, tuple(values))

    if (fetch := cur.fetchone()) is not None:
        return fetch[0]


async def record(command, *values):
    cur.execute(command, tuple(values))

    return cur.fetchone()


async def records(command, *values):
    cur.execute(command, tuple(values))

    return cur.fetchall()


async def column(command, *values):
    cur.execute(command, tuple(values))

    return [item[0] for item in cur.fetchall()]


async def execute(command, *values):
    cur.execute(command, tuple(values))


async def multi_exec(command, value_set):
    cur.executemany(command, value_set)


async def script_exec(path):
    with open(path, "r", encoding="utf-8") as script:
        cur.executescript(script.read())
