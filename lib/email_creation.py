# -*- coding: utf-8 -*-
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email import encoders
import os
import sys
from .utils import Utils
import logging
import datetime

ALERT = False
ALERT_MSG = ""
DATE = datetime.datetime.now()
logger = logging.getLogger(__name__)
pathname = os.path.abspath(os.path.dirname(sys.argv[0])) + str(os.sep)
static_path = pathname + "static" + str(os.sep)


class EmailCreation(object):

    alert = False

    def __init__(self, alert):
        self.alert = alert
        self._initialize_smtp_server()

    def _attach_img(self, filename, file_id):
        """Attache img into email
        :param filename:
        :param attachment_number:
        :return:
        """
        try:
            with open(static_path + filename, 'rb') as fp:
                # set attachment mime and file name, the image type is png
                msg_img = MIMEImage(fp.read(), name=filename)
                msg_img.add_header('Content-ID', '<{0:}>'.format(file_id))
                msg_img.add_header('Content-Disposition', 'inline', filename=filename)
                msg_img.add_header('X-Attachment-Id', '{0:}'.format(file_id))
                fp.close()
            return msg_img
        except IOError:
            logger.warning("Could not read file: " + pathname + filename)
            sys.exit(1)


    def _initialize_smtp_server(self):
        """Initialize SMTP server with TLS and authentication support
        """
        email_server = Utils.config['email_server']
        email_port = Utils.config.get('email_port', '')
        email_user = Utils.config.get('email_user', '')
        email_pass = Utils.config.get('email_pass', '')
        
        # Use default port 587 for TLS if not specified and not localhost
        if not email_port or email_port == '':
            if email_server == "localhost":
                email_port = 25
            else:
                email_port = 587
        else:
            email_port = int(email_port)
        
        try:
            # Initialize SMTP connection
            self._smtpserver = smtplib.SMTP(email_server, email_port)
            self._smtpserver.ehlo()
            
            # Use STARTTLS for non-localhost connections
            if email_server != "localhost":
                if self._smtpserver.has_extn('STARTTLS'):
                    self._smtpserver.starttls()
                    self._smtpserver.ehlo()
                    logger.info("TLS enabled for SMTP connection")
                
                # Authenticate if credentials are provided
                if email_user and email_pass:
                    self._smtpserver.login(email_user, email_pass)
                    logger.info("SMTP authentication successful")
            
            logger.info(f"SMTP server connection established to {email_server}:{email_port}")
            
        except smtplib.SMTPException as e:
            logger.error(f"SMTP connection failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize SMTP server: {str(e)}")
            raise

    def create_email(self, html, text):
        """Create email
        """
        msg_root = MIMEMultipart('related')

        msg_root['From'] = Utils.config['email_from']
        msg_root['To'] = Utils.config['email_addr']
        msg_root['CC'] = Utils.config['email_cc']
        msg_root['reply-to'] = Utils.config['email_reply_to']
        msg_root['X-Mailer'] = 'python'
        msg_root['Content-Transfer-Encoding'] = '8bit'
        msg_root['Date'] = DATE.strftime('%a, %d %b %Y  %H:%M:%S %Z')
        msg_root.preamble = 'This is a multi-part message in MIME format.'

        emails = []
        emails.append(msg_root['To'])
        emails.extend(msg_root['CC'].split(";"))

        if self.alert:
            msg_root['Subject'] = "%s %s %s Warning!" % ("[BACKUP REPORT] ", Utils.config['email_title'], DATE.strftime("%Y-%m-%d"))
            if 'X-Priority' not in msg_root:
                msg_root['X-Priority'] = "1 (Highest)"
        else:
            msg_root['Subject'] = "%s %s %s" % ("[BACKUP REPORT] ", Utils.config['email_title'], DATE.strftime("%Y-%m-%d"))

        msg_alternative = MIMEMultipart('alternative')
        msg_root.attach(msg_alternative)

        html_msg = MIMEText(html, 'html', 'utf-8')
        txt_msg = MIMEText(text, 'plain', 'utf-8')
        msg_alternative.attach(txt_msg)
        msg_alternative.attach(html_msg)

        file1 = self._attach_img("dbico.png", "0")
        msg_root.attach(file1)
        file2 = self._attach_img("hddico.png", "1")
        msg_root.attach(file2)

        if Utils.config['logo'] is not None:
            file3 = self._attach_img(Utils.config['logo'], "2")
            msg_root.attach(file3)

        logger.info("Sending email to: " + Utils.config['email_addr'] + "; " + Utils.config['email_cc'])
        self._smtpserver.sendmail(msg_root['From'], emails, msg_root.as_string())
        self._smtpserver.quit()
