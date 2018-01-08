import paramiko
import logging
import logging.config
import argparse
import datetime
import sys
import smtplib
from email.mime.txt import MIMEText
from email.utils import formataddr
import shutil

EMAIL_ADDR = ['neteric@126.com', 'tc_pilgrim@163.com']
DATETIME_FMT = '%Y/%m/%d %H:%M'

LOG_CONFIG_DICT = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
    },
    'handlers': {
        'stream_h': {
            'level': 'ERROR',
            'formatter': 'standard',
            'class': 'logging.StreamHandler',
        },
        'file_h': {
            'level': 'INFO',
            'formatter': 'standard',
            'class': 'logging.FileHandler',
            'filename': 'sys.log',
        },
    },
    'loggers': {
        '': {
            'handlers': ['stream_h', 'file_h'],
            'level': 'NOTSET',
            'propagate': True
        },
        'requests.packages': {
            'handlers': ['stream_h'],
            'level': 'NOTSET',
            'propagate': False
        },
    }
}
Logger = logging.getLogger('LenMongoDump')


class GetSSHClient(object):
    def __init__(self, conf):
        self.conf = conf

    def getssh(self):
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(self.conf.host,
                         username=self.conf.username,
                         password=self.conf.password
                         )
        return self.ssh


class ExecCmdOnServer(GetSSHClient):
    def __init__(self):
        super(ExecCmdOnServer, self).__init__()
        self.cmd = ['/opt/mongodb-linux-x86_64-3.0.1/bin/mongodump',
                    '-u', self.conf.mongo_uname,
                    '-d', self.conf.mongo_dbname,
                    '-o', self.conf.mongo_dest,
                    '-p', self.conf.mongo_passwd
                    ]

    def backup(self):
        try:
            self.ssh.exec_command(self.cmd)
        except Exception as e:
            Logger.error(e)
        else:
            pass  # TODO(ZHANGCHAO): tar backup directory
            e = 0
        finally:
            EMAIL_SUBJECT = \
                "Lenote Had Backup %s at %s " % ('Failed' if e else 'Successful',
                                                             datetime.datetime.now().strftime(DATETIME_FMT))
            EMAIL_MESSAGE_SU = \
                'Congratulations backup Leanote mongoDB successful'
            ReportBackupStatus(EMAIL_ADDR, EMAIL_SUBJECT,
                               e if e else EMAIL_MESSAGE_SU)

class DownloadBackFile(GetSSHClient):
    def __init__(self):
        super(DownloadBackFile, self).__init__()


class ReportBackupStatus(object):
    def __init__(self, reciver, mail_subject, message):
        self.smtp_server_addr = "smtp.126.com"
        self.smtp_server_port = 465
        self.smtp_server_passwd = 'XXXX'

        self.sender = 'neteric@126.com'
        self.sender_mail_postfix = '126.com'

        self.sender_alias = "Leanote server"
        self.reciver = reciver
        self.reciver_alias = "boys"

        self.message = message
        self.mail_subject = mail_subject
        self.mail()

    def mail(self):
        try:
            msg = MIMEText(self.message, 'plain', 'utf-8')
            msg['From'] = formataddr([self.sender_alias, self.sender])
            msg['To'] = formataddr([self.reciver_alias, self.reciver])
            msg['Subject'] = self.mail_subject

            server = smtplib.SMTP_SSL(self.smtp_server_addr,
                                      self.smtp_server_port)
            server.login(self.sender, self.smtp_server_passwd)
            server.sendmail(self.sender, self.reciver, msg.as_string())
            server.quit()
        except Exception as e:
            print e


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-D', '--debug', action='store_true', help='Ture debug on')
    parser.add_argument('-H', '--host', required=True, help='Domian_name or ip_addr of Leanote server')
    parser.add_argument('-u', '--username', default='root', help="username for Leanote  server")
    parser.add_argument('-p', '--password', required=True, help="passwd for Leanote  server")
    parser.add_argument('-d', '--dest', default='/backup/mongo_backup')
    #TODO(ZHANGCHAO): add mongoDB argument

    config = parser.parse_args(sys.argv[1:])
    if config.debug:
        LOG_CONFIG_DICT['LOG_CONFIG_DICT']['file_h']['level'] = 'DEBUG'
    logging.config.dictConfig(LOG_CONFIG_DICT)

    # TODO(zhangchao): args use kwargs instand
    GetSSHClient(config)


if __name__ == "__main__":
    main()
