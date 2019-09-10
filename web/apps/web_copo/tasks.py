from web.celery import app
from . import task_tt


@app.task
def my_add(group_name):
    return task_tt.task1(group_name)


@app.task
def update_ena_status():
    from submission import enareadSubmission

    enareadSubmission.EnaReads().update_study_status()
    return True
