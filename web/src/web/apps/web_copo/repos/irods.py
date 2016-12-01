__author__ = 'etuka'

from django.conf import settings
import pexpect
import re

REPOSITORIES = settings['REPOSITORIES']


def register_to_irods():
    status = ""
    remote_connect = REPOSITORIES['IRODS']['credentials']['user_token'] \
                     + "@" \
                     + REPOSITORIES['IRODS']['credentials']['host_token']
    password = REPOSITORIES['IRODS']['credentials']['password']
    program_name = REPOSITORIES['IRODS']['credentials']['program']
    script_name = REPOSITORIES['IRODS']['credentials']['script']

    cmd = "ssh {remote_connect!s} {program_name!s} {script_name!s}".format(**locals())

    thread = pexpect.spawn(cmd, timeout=None)
    thread.expect(["assword:", pexpect.EOF])
    thread.sendline(password)
    thread.expect(pexpect.EOF)
    s = thread.before.decode("utf-8")
    regex = re.compile(r'[\n\r\t]')
    s = regex.sub('', s)
    if len(s.strip(' ')) == 0:
        status = "success"
    else:
        status = "error"

    return status
