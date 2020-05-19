from web.celery import app
from submission import enareadSubmission



@app.task
def update_study_status():
    enareadSubmission.EnaReads().update_study_status()
    return True


@app.task(bind=True)
def process_ena_submission(self):
    enareadSubmission.EnaReads().process_queue()
    return True


@app.task(bind=True)
def process_ena_transfer(self):
    enareadSubmission.EnaReads().process_file_transfer()
    return True
