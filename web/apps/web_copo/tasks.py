from web.celery import app
from submission import enareadSubmission
import subprocess
import xml.etree.ElementTree as ET




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

@app.task(bind=True)
def submit_biosample(self, newspreadsheetobj, object_id, sampleobj):
    # register project to the ENA service
    curl_cmd = 'curl -u ' + newspreadsheetobj.user_token + ':' + newspreadsheetobj.pass_word \
               + ' -F "SUBMISSION=@' \
               + "submission.xml" \
               + '" -F "SAMPLE=@' \
               + "sample.xml" \
               + '" "' + newspreadsheetobj.ena_service \
               + '"'

    try:
        receipt = subprocess.check_output(curl_cmd, shell=True)
        print(receipt)
    except Exception as e:
        message = 'API call error ' + "Submitting project xml to ENA via CURL. CURL command is: " + curl_cmd.replace(
            newspreadsheetobj.pass_word, "xxxxxx")
        print(message)

    tree = ET.fromstring(receipt)
    success_status = tree.get('success')
    if success_status == 'false':  ####todo

        print(receipt)
        status = tree.find('MESSAGES').findtext('ERROR', default='Undefined error')
        # print(status)
        sampleobj.add_status(status, object_id)
        print('error')
    else:
        # retrieve id and update record
        newspreadsheetobj.get_biosampleId(receipt, object_id)