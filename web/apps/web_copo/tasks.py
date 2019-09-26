from web.celery import app
from submission import enareadSubmission


@app.task
def update_study_status():
    enareadSubmission.EnaReads().update_study_status()
    return True


@app.task
def process_ena_submission():
    enareadSubmission.EnaReads().process_queue()
    return True
