import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import web.settings.email as email_settings
from web.apps.web_copo.models import User

class CopoEmail:

    def __init__(self):
        self.messages = {
            "new_manifest":
                "<h4>New Manifest Available</h4>" +
                "<p>A new manifest has been uploaded for approval. Please follow the link to proceed</p>" +
                "<p><a href='{}'>{}</a></p>"
        }

    def __del__(self):
        self.mailserver.quit()

    def send(self, to, sub, content, html=False):
        msg = MIMEMultipart()
        msg['From'] = email_settings.mail_address

        msg['Subject'] = sub
        if html:
            msg.attach(MIMEText(content, 'html'))
        else:
            msg.attach(MIMEText(content, "plain"))
        self.mailserver = smtplib.SMTP(email_settings.mail_server, email_settings.mail_server_port)
        # identify ourselves to smtp gmail client
        self.mailserver.ehlo()
        # secure our email with tls encryption
        self.mailserver.starttls()
        # re-identify ourselves as an encrypted connection
        self.mailserver.ehlo()
        self.mailserver.login(email_settings.mail_username, email_settings.mail_password)
        self.mailserver.sendmail(email_settings.mail_address, to, msg.as_string())
        self.mailserver.quit()

    def notify_new_manifest(self, data):
        # get users in group
        users = User.objects.filter(groups__name='dtol_sample_notifiers')
        email_addresses = list()
        for u in users:
            email_addresses.append(u.email)
        msg = self.messages["new_manifest"].format(data, data)
        self.send(to=email_addresses, sub="New DToL Manifest", content=msg, html=True)