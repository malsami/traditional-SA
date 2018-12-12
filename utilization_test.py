"""Utilization-based Schedulability Test.

A general taskset is schedulable, if and only if the total utilization is less than or equal 1:
U = sum(C_i / T_i) <= 1 (neccessary condition)
"""

import logging
import utils_database as db
from TaskSet import TaskSet
from Task import Task
import math

# Global variables
_response_time_old = None
_response_time = None
_first_task = None


def utilization_test_edf(taskset):
    """Utilization-based schedulabilty test for EDF.

    Keyword arguments:
    taskset -- Taskset which should be tested, represented as a list of tuples:
                [(C0, T0), (C1, T2), ..., (Cn, Tn)]
                C0 = execution time of the first task
                T0 = period of the first task
    Return value:
    True/False -- schedulability result, True if taskset is schedulable, otherwise False
    """
    logging.debug("utilization_test(): utilization-test will be performed")
    utilization = 0
    for i in range(len(taskset)):
        utilization += taskset[i][0] / taskset[i][1]
    if utilization <= 1:
        logging.debug("utilization_test(): taskset is schedulable!")
        return True
    else:
        logging.debug("utilization_test(): taskset is NOT scheudlable!")
        return False


def utilization_test_rm(taskset):
    """Utilization-based schedulabilty test for RM.

    A taskset is schedulable with RM if U <= n(2^(1/n) - 1)

    Keyword arguments:
    taskset -- Taskset which should be tested, represented as a list of tuples:
                [(C0, T0), (C1, T2), ..., (Cn, Tn)]
                C0 = execution time of the first task
                T0 = period of the first task
    Return value:
    True/False -- schedulability result, True if taskset is schedulable, otherwise False
    """
    logging.debug("utilization_test(): utilization-test will be performed")
    utilization = 0
    for i in range(len(taskset)):
        utilization += taskset[i][0] / taskset[i][1]
    utilization_bound = len(taskset) * (2**(1/len(taskset)) - 1)
    if utilization <= utilization_bound:
        logging.debug("utilization_test(): taskset is schedulable!")
        return True
    else:
        logging.debug("utilization_test(): taskset is NOT scheudlable!")
        return False


def fp_sufficient_test(new_task, rq_buf):
    """Sufficient schedulability test for fixed priority.

    Test from argos-research/genode-AdmCtrl.
    Keyword arguments:
    taskset -- the taskset that should be tested
    Return value:
    True/False -- result of schedulability test (True if taskset is schedulable, otherwise False)
    """
    num_elements = len(rq_buf)
    if num_elements == 0:      # Task set has only one task -> taskset is schedulable
        logging.debug("Taskset has only one task --> is schedulable!")
        return True

    R_ub, sum_util, sum_util_wcet = 0.0, 0.0, 0.0
    curr_task_idx = 0
    _curr_task = rq_buf[curr_task_idx]
    logging.debug("Current Task = " + str(_curr_task))

    for i in range(num_elements):
        # Add new_task if priority bigger then curr_task
        if new_task.priority >= _curr_task.priority:
            R_ub = new_task.executionTime + sum_util_wcet / (1 - sum_util)
            logging.debug("R_ub: {0:d}.{1:d} at new_task position {2:d}, deadline: {3:d}".format(int(R_ub), int(R_ub*100-int(R_ub)*100), i, new_task.deadline))
            if R_ub > new_task.deadline:    # Deadline hit for new task
                logging.debug("Deadline hit for task {0:d}, Taskset might be not schedulable! Maybe try an exact test.".format(i))
                return False
            sum_util += new_task.executionTime / new_task.period
            sum_util_wcet += new_task.executionTime * (1 - (new_task.executionTime /
                                                            new_task.period))
        R_ub = (_curr_task.executionTime + sum_util_wcet) / (1 - sum_util)
        logging.debug("R_ub: {0:d}.{1:d} at position {2:d}, deadline: {3:d}".format(int(R_ub), int(R_ub*100 - int(R_ub*100)), i, _curr_task.deadline))

        if R_ub > _curr_task.deadline:      # Deadline hit for task i
            logging.debug("Deadline hit for task {0:d}, Taskset might be not schedulable! Maybe try an exact test.".format(i))
            return False
        sum_util += _curr_task.executionTime / _curr_task.period
        sum_util_wcet += _curr_task.executionTime * (1 - (_curr_task.executionTime / _curr_task.period))
        curr_task_idx += 1
        if curr_task_idx < num_elements:
            _curr_task = rq_buf[curr_task_idx]
            logging.debug("Current Task = " + str(_curr_task))

    # Add new_task if not done before
    if new_task.priority < _curr_task.priority:
        R_ub = (new_task.executionTime + sum_util_wcet) / (1 - sum_util)
        logging.debug("R_ub = {0:d}.{1:d} at end, deadline = {2:d}".format(int(R_ub), int(R_ub*100 - int(R_ub*100)), new_task.deadline))
        if R_ub > new_task.deadline:
            logging.debug("Deadline hit for new task {0:d}, Taskset might be not schedulable! Maybe try an exact test.".format(curr_task_idx))
            return False
        logging.debug("Upper bound lower then deadline -> taskset is schedulable!")
    return True


if __name__ == "__main__":
    # Configure logging: format should be "LEVELNAME: Message",
    # logging level should be DEBUG (all messages are shown)
    logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)

    db_connection = db.openDb(db.db_name)       # Open database
    db_cursor = db_connection.cursor()          # Create a cursor for database

    # Read execution times depending on PKG and save as dictionary
    dict_C = {}     # Empty dictionary
    # Iterate over all table rows
    for row in db_cursor.execute("SELECT * FROM ExecutionTimes"):
        dict_C[row[0]] = row[1]     # Add entry "PKG" : "Execution Time"

    table_name = "Dataset3"     # Name of the table

    # Get number of columns of the table
    db_cursor.execute("PRAGMA table_info('" + table_name + "')")
    numberOfColumns = len(db_cursor.fetchall())

    # Calculate number of tasks in dataset
    # -2 for Set_ID and Exit_Value
    # /8 because each task has 8 properties
    numberOfTasks = int((numberOfColumns - 2) / 8)

    row_counter = 0

    # Read out the table and perform the test for each taskset in table
    for row in db_cursor.execute("SELECT * FROM " + table_name):
        if row_counter <= 10:
            taskset = TaskSet()     # Empty taskset
            schedulability = None
            # Iterate over all tasks
            for i in range(numberOfTasks):
                C = dict_C[row[4+i*8]]      # Execution time of task i
                new_task = Task(priority=row[1+i*8], deadline=row[2+i*8], quota=row[3+i*8], pkg=row[4+i*8], arg=row[5+i*8], period=row[6+i*8], numberOfJobs=row[7+i*8], offset=row[8+i*8], executionTime=C)
                schedulability = fp_sufficient_test(new_task, taskset)
                # schedulability = RTA(new_task, taskset)
                logging.debug("Schedulability = " + str(schedulability))
                taskset.addTask(new_task)
            if schedulability == True:
                print("Task-Set is schedulable!")
            else:
                print("Task-Set is NOT schedulable!")
            row_counter += 1

    db.closeDb(db_connection)       # Close database
