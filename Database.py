"""For the new database 'panda_v1'."""
import logging  # for logging
import math  # for ceil-function
import os
import sqlite3  # for working with the database

from Task import Task  # for creating tasks
from Taskset import Taskset  # for creating task-sets

# attributes of the database
db_dir = os.path.dirname(
    os.path.abspath(__file__))  # path to the database = current working directory
db_name = "panda_v2.db"  # name of the database

_db_connection = None  # connection to the database
_db_cursor = None  # cursor for working with the database
_current_taskset = 0  # index of next un-read task-set

# task execution times
_execution_time = {
    ("hey", 0): (1045, 1045, 1045),
    ("hey", 1000): (1094, 1094, 1094),
    ("hey", 1000000): (1071, 1071, 1071),

    ("pi", 100): (1574, 1574, 1574),
    ("pi", 10000): (1693, 1693, 1693),
    ("pi", 100000): (1870, 1870, 1870),

    ("cond_42", 41): (1350, 1350, 1350),
    ("cond_42", 42): (1376, 1376, 1376),
    ("cond_42", 10041): (1413, 1413, 1413),
    ("cond_42", 10042): (1432, 1432, 1432),
    ("cond_42", 1000041): (1368, 1368, 1368),
    ("cond_42", 1000042): (1396, 1396, 1396),

    ("cond_mod", 100): (1323, 1323, 1323),
    ("cond_mod", 103): (1351, 1351, 1351),
    ("cond_mod", 10000): (1395, 1395, 1395),
    ("cond_mod", 10003): (1391, 1391, 1391),
    ("cond_mod", 1000000): (1342, 1342, 1342),
    ("cond_mod", 1000003): (1391, 1391, 1391),

    ("tumatmul", 10): (1511, 1511, 1511),
    ("tumatmul", 11): (1543, 1543, 1543),
    ("tumatmul", 10000): (1692, 1692, 1692),
    ("tumatmul", 10001): (1662, 1662, 1662),
    ("tumatmul", 1000000): (3009, 3009, 3009),
    ("tumatmul", 1000001): (3121, 3121, 3121),

    "hey": (1070, 1070, 1070),
    "pi": (1712, 1712, 1712),
    "cond_42": (1389, 1389, 1389),
    "cond_mod": (1366, 1366, 1366),
    "tumatmul": (2090, 2090, 2090)
}

# Which type of execution time should be used?
# 0: minimum execution time (BCET, best case execution time)
# 1: maximum execution time (WCET, worst case execution time)
# 2: average execution time
_C_Type = 2


# Open database
def open_DB():
    """Open the database.

    If the database can be found, a connection and cursor is created and saved.
    If there is no database file defined through db_dir and db_name,
    an error message is printed.
    """
    global db_name
    db_path = db_dir + "\\" + db_name

    # Check if database exists
    if os.path.exists(db_path):  # database exists
        global _db_connection, _db_cursor
        _db_connection = sqlite3.connect(db_path)
        _db_cursor = _db_connection.cursor()
    else:  # database does not exist
        logging.error("new_database/open_DB(): Database '" + db_name + "' not found!")


# Close database
def close_DB():
    """Close the database.

    If the database is open, the changes are saved before the database is closed.
    """
    global _db_connection, _db_cursor
    if _db_connection is not None:  # database is open
        _db_connection.commit()
        _db_connection.close()
        _db_connection = None
        _db_cursor = None
    else:  # database is already closed
        logging.debug("new_database/close_DB(): No open database!")


# Get dataset
def get_dataset():
    """Get a dataset.

    Reads all task-sets from the database.
    Return values:
        list with task-sets as Taskset-Objects
        None -- dataset is empty
        -1 -- an error occurred
    """

    # Open database if not connected
    global _db_connection, _db_cursor
    if _db_connection is None or _db_cursor is None:
        open_DB()

    # Read execution times from the database
    read_execution_times()

    # Read all task-sets from the database
    _db_cursor.execute("SELECT * FROM TaskSet")
    rows = _db_cursor.fetchall()

    close_DB()  # close database

    dataset = []  # create empty list

    if len(rows) == 0:  # dataset is empty
        logging.debug("new_database/get_dataset(): the dataset is empty!")
        return None

    # Limit number of rows
    rows = rows[:100]

    # iterate over all rows
    for row in rows:
        id = row[0]
        result = row[1]
        task_ids = row[2:]

        # Create empty task-set
        new_taskset = Taskset(id=id, result=result, tasks=[])

        # iterate over all tasks and create task-set
        for task_id in task_ids:
            if task_id != -1:  # valid task-id
                new_task = get_task(task_id)  # get task from database
                new_taskset.add_task(new_task)  # add task to task-set

        # Add task-set to dataset
        dataset.append(new_taskset)

    # return created dataset
    return dataset


# Get task-set
def get_taskset(id):
    """Get a task-set.

    If no arguments are given, the task-set at index _current_taskset is returned.
    Input arguments:
        idx -- index of the task-set, corresponds to id of task-set (column Set-ID)
    Return value:
        the task-set
        None -- no more task-set available
        -1 -- an error occurred
    """

    # Check input argument - must be a positive integer number
    if not isinstance(id, int) or id < 0:  # invalid input
        logging.error(
            "new_database/get_taskset(): invalid input argument - must be an positive int!")
        return -1

    # Open database if not connected
    global _db_connection, _db_cursor
    if _db_connection is None or _db_cursor is None:
        open_DB()

    # Read the task-set from the database
    _db_cursor.execute("SELECT * FROM TaskSet WHERE Set_ID = ?", (id,))
    row = _db_cursor.fetchall()

    close_DB()  # close database

    if len(row) == 0:  # no task-set with Set_ID = id found
        logging.debug("new_database/get_taskset(): no task-set with ID = " + str(id) + " found!")
        return None
    elif len(row) > 1:  # more than one task-set with Set_ID = id found
        logging.error(
            "new_database/get_taskset(): something went wrong - more than one task-set with ID = " + str(
                id) + " found")
        return -1
    else:  # one task-set was found
        # Extract task-set attributes
        id = row[0][0]
        result = row[0][1]
        task_ids = row[0][2:]

        # Create empty task-set
        new_taskset = Taskset(id=id, result=result, tasks=[])

        # Iterate over all tasks and create task-set
        for task_id in task_ids:
            if task_id != -1:  # Valid task-id
                new_task = get_task(task_id)  # get task from database
                new_taskset.add_task(new_task)  # add task to task-set

        # return created task-set
        return new_taskset


# Get task
def get_task(id):
    """Read a task from the database.

    Extracts the attributes of a task with the Task-ID defined by id and creates a new task-object.
    Input arguments:
        id -- id of the task, corresponds to Task_ID
    Return values:
        task
        None -- no task found
        -1 -- an error occurred
    """

    # Check input argument - must be a positive integer number
    if not isinstance(id, int) or id < 0:  # invalid input
        logging.error("new_database/get_task(): invalid input argument - must be an positive int!")
        return -1

    # Open database if not connected
    global _db_connection, _db_cursor
    if _db_connection is None or _db_cursor is None:
        open_DB()

    # Read the task defined by id
    _db_cursor.execute("SELECT * FROM Task WHERE Task_ID = ?", (id,))
    row = _db_cursor.fetchall()

    close_DB()  # close database

    # Check number of rows
    if len(row) == 0:  # no task with Task_ID = id found
        logging.debug("new_database/get_task(): no task with Task_ID = " + str(id) + "found!")
        return None
    elif len(row) > 1:  # more than one task with Task_ID = id found
        logging.error(
            "new_database/get_task(): more than one task with Task_ID = " + str(id) + " found!")
        return -1
    else:  # one task was found
        # Extract attributes of the task
        id = row[0][0]
        priority = row[0][1]
        pkg = row[0][5]
        arg = row[0][6]
        deadline = row[0][9]
        period = row[0][10]
        number_of_jobs = row[0][11]

        # Define execution time depending on pkg and arg
        if (pkg, arg) in _execution_time:  # combination of pkg and arg exists
            execution_time = _execution_time[(pkg, arg)][_C_Type]
        else:  # combination of pkg and arg does not exist
            # use only pkg to determine execution time
            execution_time = _execution_time[pkg][_C_Type]

        # Create new task
        new_task = Task(id=id, priority=priority, pkg=pkg, arg=arg, deadline=deadline,
                        period=period, number_of_jobs=number_of_jobs, execution_time=execution_time)

        # Return created task
        return new_task


# get all tasks
def get_all_tasks():
    """Read all tasks from the database.

    Extracts the attributes of all tasks and creates a list of task-objects.
    Return:
        list with all tasks
        -1 - an error occurred
    """

    # open database if not connected
    global _db_connection, _db_cursor
    if _db_connection is None or _db_cursor is None:
        open_DB()

    # read all tasks
    _db_cursor.execute("SELECT * FROM Task")
    rows = _db_cursor.fetchall()

    # close database
    close_DB()

    # check number of rows
    if len(rows) < 1:  # no tasks found
        logging.error("database.py/get_all_tasks(): no tasks found!")
        return -1
    else:  # at least one task was found
        task_list = []  # empty list for tasks
        # iterate over all rows, extract attributes and create task
        for row in rows:
            id = row[0]
            priority = row[1]
            pkg = row[5]
            arg = row[6]
            deadline = row[9]
            period = row[10]
            number_of_jobs = row[11]

            new_task = Task(id=id, priority=priority, pkg=pkg, arg=arg, deadline=deadline,
                            period=period, number_of_jobs=number_of_jobs)

            task_list.append(new_task)
        return task_list


# get all jobs of a task
def get_jobs_C(task_id):
    """Read all jobs of a task from the database.

    Extracts the attributes of all jobs of a task defined by task_id.
    Args:
        task_id - id of the task which jobs are wanted
    Return:
        list with execution times of jobs
        -1 -  an error occured
    """
    # Check input argument - must be a positive integer number
    if not isinstance(task_id, int) or task_id < 0:
        logging.error(
            "database.py/get_jobs(): invalid input argument - must be a positive int!")
        return -1

    # Open database if not connected
    global _db_connection, _db_cursor
    if _db_connection is None or _db_cursor is None:
        open_DB()

    # Read all jobs of task defined by task_id that where executed successful (Exit_Value = EXIT)
    _db_cursor.execute("SELECT * FROM Job WHERE Task_ID = ? AND Exit_Value = ?", (task_id, "EXIT"))
    rows = _db_cursor.fetchall()

    # close database
    close_DB()

    # Check number of rows
    if len(rows) == 0:  # no jobs found
        logging.error("database.py/get_jobs(): no jobs for Task-ID " + str(task_id) + " found!")
        return -1

    # create empty list for execution times
    execution_times = []

    # For each job extract attributes and create a new job-object
    for row in rows:
        start_date = row[3]
        end_date = row[4]
        execution_time = end_date - start_date

        if (execution_time > 0):
            execution_times.append(execution_time)

    return execution_times


# save execution times of tasks
def save_execution_times(task_dict):
    """Save execution times in the database.

    Saves the given execution times to the database. The values of a key consist of (min_C, max_C, average_C)
    Args:
        task_dict - dictionary with task execution times
    """
    # Open database if not connected
    global _db_connection, _db_cursor
    if _db_connection is None or _db_cursor is None:
        open_DB()

    # create table "ExecutionTimes" if it does not exist
    create_table_sql = "CREATE TABLE IF NOT EXISTS ExecutionTimes (" \
                       "[PKG(Arg)] text PRIMARY KEY, " \
                       "[Min_C] integer, " \
                       "[Max_C] integer, " \
                       "[Average_C] integer" \
                       ");"
    try:
        _db_cursor.execute(create_table_sql)
    except sqlite3.Error as e:
        print(e)

    # sql statement for inserting or replacing a row in the ExecutionTimes table
    insert_or_replace_sql = "INSERT OR REPLACE INTO ExecutionTimes([PKG(Arg)], Min_C, Max_C, Average_C) VALUES(?, ?, ?, ?)"

    # iterate over all dictionary keys
    for key in task_dict:
        # insert or replace the row with the given execution times
        if isinstance(key, str):  # key = (PKG)
            _db_cursor.execute(insert_or_replace_sql,
                               (key, task_dict[key][0], task_dict[key][1], task_dict[key][2]))
        elif len(key) == 2:  # key is combination of pkg and arg: key = (PKG, Arg)
            _db_cursor.execute(insert_or_replace_sql, (
                key[0] + "(" + str(key[1]) + ")", task_dict[key][0], task_dict[key][1],
                task_dict[key][2]))

    # save (commit) the changes
    _db_connection.commit()

    # close database
    close_DB()


# read execution times of tasks
def read_execution_times():
    """Read the execution times of the tasks from the database.

    The minimum, maximum and average execution times of all tasks are saved in the table ExecutionTimes.
    If this table is not present in the database, the default execution times in _default_execution_times are used.

    Return:
        -1 - an error occurred
    """
    # open database if not connected
    global _db_connection, _db_cursor
    if _db_connection is None or _db_cursor is None:
        open_DB()

    # read table ExecutionTimes
    _db_cursor.execute("SELECT * FROM ExecutionTimes")
    rows = _db_cursor.fetchall()

    # check if execution times where found
    if len(rows) == 0:  # now row was read
        logging.error(
            "database.py/read_execution_times(): table ExecutionTimes does not exist or is empty!")
        return -1

    # update execution time dictionary
    for row in rows:  # iterate over all rows
        # get data from row
        pkg_arg = row[0]
        min_C = row[1]
        max_C = row[2]
        average_C = row[3]
        
        # TODO: delete rounding
        average_C = math.ceil(average_C)

        # split pkg and arg and create dictionary entry
        if '(' in pkg_arg:  # string contains pkg and arg
            pkg, arg = pkg_arg.split('(')
            arg = int(arg[:-1])  # delete last character = ')' and format to int
            dict_entry = {(pkg, arg): (min_C, max_C, average_C)}
        else:  # string contains only pkg, no arg
            pkg = pkg_arg
            dict_entry = {pkg: (min_C, max_C, average_C)}

        # update dictionary
        _execution_time.update(dict_entry)


if __name__ == "__main__":
    # Configure logging: format should be "LEVELNAME: Message",
    # logging level should be DEBUG (all messages are shown)
    logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.DEBUG)
    dataset = get_dataset()
    print(dataset[0])
