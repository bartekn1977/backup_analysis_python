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


    def _get_smtp_port(self, email_server, email_port):
        """Determine SMTP port to use"""
        if not email_port or email_port == '':
            return 25 if email_server == "localhost" else 587
        return int(email_port)

    def _connect_smtp_ssl(self, email_server, email_port):
        """Connect using SSL/TLS (port 465)"""
        server = smtplib.SMTP_SSL(email_server, email_port)
        server.ehlo()
        logger.info(f"SSL/TLS connection established to {email_server}:{email_port}")
        return server

    def _connect_smtp_starttls(self, email_server, email_port):
        """Connect using STARTTLS (port 587 or others)"""
        server = smtplib.SMTP(email_server, email_port)
        server.ehlo()
        
        if email_server != "localhost" and server.has_extn('STARTTLS'):
            server.starttls()
            server.ehlo()
            logger.info(f"STARTTLS enabled for SMTP connection to {email_server}:{email_port}")
        
        return server

    def _authenticate_smtp(self, email_server, email_user, email_pass):
        """Authenticate with SMTP server if credentials provided"""
        if email_server != "localhost" and email_user and email_pass:
            self._smtpserver.login(email_user, email_pass)
            logger.info("SMTP authentication successful")

    def _initialize_smtp_server(self):
        """Initialize SMTP server with SSL/TLS and authentication support
        Supports both port 465 (SSL/TLS) and port 587 (STARTTLS)
        """
        email_server = Utils.config['email_server']
        email_port = Utils.config.get('email_port', '')
        email_user = Utils.config.get('email_user', '')
        email_pass = Utils.config.get('email_pass', '')
        
        email_port = self._get_smtp_port(email_server, email_port)
        
        try:
            # Port 465 uses SSL/TLS, others use STARTTLS
            if email_port == 465:
                self._smtpserver = self._connect_smtp_ssl(email_server, email_port)
            else:
                self._smtpserver = self._connect_smtp_starttls(email_server, email_port)
            
            # Authenticate if needed
            self._authenticate_smtp(email_server, email_user, email_pass)
            
            logger.info(f"SMTP server connection ready: {email_server}:{email_port}")
            
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

        background_pattern = self._attach_img("background-pattern-neutral.png", "3")
        msg_root.attach(background_pattern)

        background_top = self._attach_img("background-top-neutral.png", "4")
        msg_root.attach(background_top)

        db_icon = self._attach_img("dbico.png", "2")
        msg_root.attach(db_icon)
        hdd_icon = self._attach_img("hddico.png", "1")
        msg_root.attach(hdd_icon)

        

        if Utils.config['logo'] is not None:
            logo_file = self._attach_img(Utils.config['logo'], "5")
            msg_root.attach(logo_file)

        logger.info("Sending email to: " + Utils.config['email_addr'] + "; " + Utils.config['email_cc'])
        self._smtpserver.sendmail(msg_root['From'], emails, msg_root.as_string())
        self._smtpserver.quit()
