#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Time    : 18/1/6 10:36
# Author  : Eric.Zhang

import paramiko
import logging
import logging.config
import argparse
import datetime
import sys, os
import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr

EMAIL_ADDR = ['neteric@126.com', 'tc_pilgrim@163.com']
DATETIME_FMT = '%Y/%m/%d %H:%M'
TIME_FMT = '%Y%m%d%H%M'
NOW_TIME = datetime.datetime.now().strftime(DATETIME_FMT)
NOW = datetime.datetime.now().strftime(TIME_FMT)
E_SUBJECT_F = "Leanote Had Backup Failed at %s " % (NOW_TIME)
E_SUBJECT_S = "Leanote Had Backup Successful at %s " % (NOW_TIME)
E_MESSAGE_S = "Congratulations! you had backup database data successful!"
LOG_CONFIG_DICT = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
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
    }
}
Logger = logging.getLogger('LeMongoDump')


class GetSSHClient(object):
    def __init__(self, conf):
        self.conf = conf

    def work(self):
        try:
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh.connect(self.conf.host,
                             username=self.conf.username,
                             password=self.conf.password
                             )
        except Exception as e:
            Logger.error(e)
            E_MESSAGE_F = 'Backup Leanote mongoDB Faild as Following: %s' % e
            ReportBackupStatus(EMAIL_ADDR, E_SUBJECT_F, E_MESSAGE_F)
            sys.exit()

        else:
            Logger.info("Get ssh connection successful!")
            return self.ssh


class ExecCmdOnServer(GetSSHClient):
    def __init__(self, conf, ssh):
        self.conf = conf
        self.ssh = ssh
        self.conf.dest = os.path.abspath(self.conf.dest)
        self.cmd_mkdir = "/usr/bin/mkdir -p %s" % os.path.join(self.conf.dest, NOW)
        self.DEST = os.path.join(self.conf.dest, NOW)
        self.backup_file = "%s/mongo_backup_%s.tar.gz" % (self.conf.dest, NOW)
        self.cmd_tar = 'tar -zcvf %s %s' % (self.backup_file, self.DEST)
        self.cmd_backup = "{0} {1} {2} {3} {4}".format('/opt/mongodb-linux-x86_64-3.0.1/bin/mongodump',
                                                       '-u %s' % self.conf.mongo_uname,
                                                       '-p %s' % self.conf.mongo_passwd,
                                                       '-d %s' % self.conf.mongo_dbname,
                                                       '-o %s' % self.DEST
                                                       )

    def run(self, cmds):
        Logger.info("Runing cmd: %s" % cmds)
        stdin, stdout, stderr = self.ssh.exec_command(cmds)
        return stderr.readlines() if stderr.readlines() else ''

    def checkdir(self):
        if self.run(self.cmd_mkdir):
            Logger.error("mkdir error")
        else:
            self.backup()

    def backup(self):
        e = self.run(self.cmd_backup)
        if 'error' in e:
            Logger.error('Exec Commend by SSH Occer Error as:  %s' % e)
            E_MESSAGE_F = 'Backup Leanote mongoDB Faild as Following: %s' % e
            ReportBackupStatus(EMAIL_ADDR, E_SUBJECT_F, E_MESSAGE_F)
        else:
            Logger.info("db backup to %s success", self.conf.dest)
            self.makearchive()

    def makearchive(self):
        if self.run(self.cmd_tar):
            Logger.error("exec cmd %s error" % self.cmd_tar)
        else:
            Logger.info("make archive success")
            DownloadBackFile(self.conf, self.backup_file)


class DownloadBackFile(GetSSHClient):
    def __init__(self, conf, backup_file):
        super(DownloadBackFile, self).__init__(conf)
        self.conf = conf
        self.backup_file = backup_file
        self.transfile()

    def transfile(self):
        try:
            trans = paramiko.Transport(self.conf.host)
            trans.connect(username=self.conf.username, password=self.conf.password)
            sftp_ins = paramiko.SFTPClient.from_transport(trans)
            sftp_ins.get(self.backup_file, self.backup_file)
        except Exception as e:
            Logger.error('Download Error as %s' % e)
            E_MESSAGE_F = 'Download Error as %s' % e
            ReportBackupStatus(EMAIL_ADDR, E_SUBJECT_F, E_MESSAGE_F)
        else:
            ReportBackupStatus(EMAIL_ADDR, E_SUBJECT_S, E_MESSAGE_S)


class ReportBackupStatus(object):
    def __init__(self, reciver, mail_subject, message):
        self.smtp_server_addr = "smtp.126.com"
        self.smtp_server_port = 465
        self.smtp_server_passwd = 'xxxx'
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
            Logger.error("SedMail failed as: %s" % e)
            print e


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-D', '--debug', action='store_true', help='Ture debug on')
    parser.add_argument('-H', '--host', required=True, help='Domian_name or ip_addr of Leanote server')
    parser.add_argument('-u', '--username', default='root', help="username for Leanote  server")
    parser.add_argument('-p', '--password', required=True, help="passwd for Leanote  server")
    parser.add_argument('-d', '--dest', default='/back')
    parser.add_argument('--mongo_uname', default='root', help="username of MongoDB")
    parser.add_argument('--mongo_passwd', required=True, help="passwd of MongoDB")
    parser.add_argument('--mongo_dbname', default='leanote', help="DB need to backup")
    config = parser.parse_args(sys.argv[1:])
    if config.debug:
        LOG_CONFIG_DICT['handlers']['file_h']['level'] = 'DEBUG'
    logging.config.dictConfig(LOG_CONFIG_DICT)
    if not os.path.exists(config.dest):
        os.mkdirs(config.dest)

    ssh = GetSSHClient(config).work()
    ExecCmdOnServer(config, ssh).checkdir()


if __name__ == "__main__":
    main()
