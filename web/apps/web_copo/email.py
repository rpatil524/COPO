import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from web.settings.email import *


class CopoEmail:

    def __init__(self):
        pass


    def __del__(self):
        self.mailserver.quit()

    def send(self, to, sub, content, html=False):
        msg = MIMEMultipart()
        msg['From'] = mail_address
        msg['To'] = to
        msg['Subject'] = sub
        if html:
            msg.attach(MIMEText(content, 'html'))
        else:
            msg.attach(MIMEText(content, "plain"))
        self.mailserver = smtplib.SMTP(mail_server, mail_server_port)
        # identify ourselves to smtp gmail client
        self.mailserver.ehlo()
        # secure our email with tls encryption
        self.mailserver.starttls()
        # re-identify ourselves as an encrypted connection
        self.mailserver.ehlo()
        user = mail_username
        password = mail_password
        self.mailserver.login(user, password)
        self.mailserver.sendmail(mail_address, to, msg.as_string())
        self.mailserver.quit()