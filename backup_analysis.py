#!/usr/bin/env python3
"""
Backup and Tablespace Analysis
for ORACLE databases

ver. 3.19.0
author: Bart!
(C) data4IT, 2024

Requirements:
    yum install python-pip python-devel python-markupsafe cyrus-sasl-plain -y
    pip install oracledb
    pip install texttable
    pip install Jinja2

Script usage:
    backup_analysis.py -q
    backup_analysis.py -q -f config_file
    backup_analysis.py -v

Changelog
    3.15.0 - separete modules into files; setup jinja2 templates
    3.15.6 - use setup tools to build package
    3.15.7 - move disk usage to submodules
    3.15.8 - rise error when cannot connect to database
    3.16.1 - add multitenancy support
    3.16.2 - update email header setup when warning need to be added
    3.16.4 - logger fixups, amms_infra.certs
    3.17.0 - formatting updates
    3.20.0 - refactor to be used with python3
    3.21.0 - use oracledb instead of cx_Oracle, add dataguard status, add docker version check

"""

__ver__ = "3.21.0"

import os
import sys
import ctypes

import datetime
import threading
import logging
import configparser

import texttable
from jinja2 import Environment, FileSystemLoader
from lib.utils import Utils
from lib.database_tests import DatabaseTests
from lib.database_usage import DatabaseUsage
from lib.email_creation import EmailCreation

ALERT = False
ALERT_MSG = ""
LOG_FORMAT = "[%(asctime)s, %(name)s, %(threadName)s, %(levelname)s] %(message)s"
pathname = os.path.abspath(os.path.dirname(sys.argv[0])) + str(os.sep)
logging.basicConfig(filename=pathname + "log" + str(os.sep) + "backup_analysis.log", level=logging.INFO, format=LOG_FORMAT)
DATE = datetime.datetime.now()
logging.info("Report start: %s" % DATE.strftime("%d-%m-%Y"))
env = Environment(loader=FileSystemLoader('%s/templates/' % os.path.dirname(__file__)))


def fs_df(db_fs):
    """Gets filesystem parameters
    """
    ret_val = {}
    global ALERT
    global ALERT_MSG
    result = []
    for i in db_fs:
        logging.info("Filesystem storage usage: " + i)
        if os.name == 'nt':
            total, used, free = Utils.disk_usage_win(i)
        else:
            total, used, free = Utils.disk_usage_linux(i)
        total = float(total // (2**30))
        used = float(used // (2**30))
        free = float(free // (2**30))
        pct_free = float((free / total)*100)
        result.append([i, total, used, free, pct_free])
        if float(pct_free) <= float(Utils.config["threshold"]):
            ALERT = True
            ALERT_MSG += "<p>&raquo; " + i + " filesystem has not enought space</p>"
            logging.warning(i + " filesystem has not enought space")

    template = env.get_template('fs_size.html.j2')
    ret_val["html"] = template.render(data=result, threshold=Utils.config["threshold"])
    ret_val["txt"] = Utils.create_txt_table(result, ["Oracle data Filesystem", "Total space [GB]", "Used space [GB]",
                                                     "Free space [GB]", "Free perc. [%]"])
    return ret_val


def asm_df(dbs):
    """Gets ASM parameters
    """
    ret_val = {}
    global ALERT
    global ALERT_MSG
    logging.info("ASM storage usage")
    con = DatabaseUsage(dbs)
    sql = """\
SELECT
    name,
    round(total_mb/1024) total_gb,
    round((total_mb-free_mb)/1024) as used_gb,
    round((free_mb)/1024) free_gb,
    round(100 * (free_mb/total_mb),2) free_perc
FROM
    v$asm_diskgroup
"""
    result = con.execute_query(sql, None)
    con.close_db()

    template = env.get_template('fs_size.html.j2')
    ret_val["html"] = template.render(data=result, threshold=Utils.config["threshold"])

    ret_val["txt"] = Utils.create_txt_table(result, ["Oracle ASM Diskgroup", "Total space [GB]", "Used space [GB]",
                                                     "Free space [GB]", "Free perc. [%]"])
    return ret_val


def render_table(caption, full_title, db_name, table_html, id_postfix):
    """Renders table test content
    """
    logging.info("%s %s" % (caption, db_name))
    template = env.get_template('test_table.html.j2')
    html = template.render(caption=caption, full_title=full_title, dbname=db_name, table_html=table_html, postfix=id_postfix)
    return html


def db_test(dbs, results, i, check_logs = False, app_version = False, lob_check = False,
            multitenant = False, dataguard = False):
    """Execute tests on database
    """
    db = DatabaseTests(dbs)

    logging.info("Executiong on %s" % dbs["db"].upper())

    alert = False
    alert_msg = ""

    # Database version
    ret_val = db.db_version()
    db_version_result = ret_val['version']
    logging.info("%s ver.: %s" % (dbs["db"].upper(), db_version_result))

    # APPs versions
    app_version_result = ""
    if app_version:
        if app_version == 'amms':
            logging.info("Checking AMMS version %s" % dbs["db"].upper())
            ret_val = db.amms_version()
            app_version_result = ret_val['version']
        if app_version == 'im':
            logging.info("Checking IM version %s" % dbs["db"].upper())
            ret_val = db.im_version()
            app_version_result = ret_val['version']
        if app_version == 'docker':
            logging.info("Checking Docker App version %s" % dbs["db"].upper())
            ret_val = db.docker_version()
            app_version_result = ret_val['version']

    # if dataguard
    if dataguard:
        dg_status = Utils.get_dg_status(dbs["db"])
    else:
        dg_status = None

    # DBID for RMAN
    ret_val = db.dbid()
    dbid = ret_val["dbid"]
    logging.info("%s DBID %s" % (dbs["db"].upper(), str(dbid)))

    # DB Title
    # if multitenant get PDBs
    if multitenant:
        pdb_val = db.pdbs()
        template = env.get_template('db_title_cdb.html.j2')
        html_content = template.render(dbname=dbs["db"], dbid=dbid, check_logs=check_logs, lob_check=lob_check, pdb_val=pdb_val, dg_status=dg_status, db_version=db_version_result)
        text_content = "=== Database: %s (DBID: %s, ver.: %s) ===\n\n" % (dbs["db"].upper(), dbid, db_version_result)
        if dataguard:
            text_content += " DataGuard status: {0:}\n".format(dg_status)
        for pdb in pdb_val:
            text_content += " * {0:} ({1:})\n".format(pdb['pdb'], pdb['guid'])
    else:
        template = env.get_template('db_title.html.j2')
        html_content = template.render(dbname=dbs["db"], dbid=dbid, check_logs=check_logs, lob_check=lob_check, dg_status=dg_status, db_version=db_version_result)
        text_content = "=== Database: %s (DBID: %s, ver.: %s) ===\n\n" % (dbs["db"].upper(), dbid, db_version_result)
        if dataguard:
            text_content += " DataGuard status: {0:}\n".format(dg_status)

    # DB size
    if multitenant:
        ret_val = db.cdb_db_size()
    else:
        ret_val = db.db_size()
    text_content += "%s\n" % ret_val["txt"]
    db_size = ret_val["size"]
    logging.info("Database size " + dbs["db"].upper() + " " + str(db_size))

    # FRA usage
    text_content += "--- Fast Recovery Area ---\n"
    ret_val = db.fra_usage()
    text_content += "%s\n" % ret_val["txt"]
    html_content += render_table("Fast Recovery Area", "Raport zajętość Fast Recovery Area:", dbs["db"], ret_val["html"], "fra")

    # Full backup
    text_content += "--- Full backup ---\n"
    ret_val = db.full_bck(dbs["db"].upper())
    text_content += "%s\n" % ret_val["txt"]
    html_content += render_table("Full backup", "Raport wykonania kopii pełnych:", dbs["db"], ret_val["html"], "full")
    if ret_val["alert"] or alert:
        alert = True
        alert_msg += ret_val["alert_msg"]

    # Archivelog backup
    text_content += "--- Archivelog ---\n"
    ret_val = db.arch_bck(dbs["db"].upper())
    text_content += "%s\n" % ret_val["txt"]
    html_content += render_table("Archivelog", "Raport wykonania kopii archive-logów:", dbs["db"], ret_val["html"], "arch")
    if ret_val["alert"] or alert:
        alert = True
        alert_msg += ret_val["alert_msg"]

    # Logs stats
    if check_logs:
        text_content += "--- Logs info ---\n"
        ret_val = db.logs_test()
        text_content += "%s\n" % ret_val["txt"]
        html_content += render_table("Logs info", "Raport z migracji logów aplikacji:", dbs["db"], ret_val["html"], "logs")

    # AMMS certs
    if app_version:
        if app_version == 'amms':
            text_content += "--- AMMS Certs ---\n"
            ret_val = db.amms_infra_certs()
            text_content += "%s\n" % ret_val["txt"]
            html_content += render_table("AMMS cert", "Informacje o certyfikatach AMMS:", dbs["db"], ret_val["html"], "cert")

    # Redo rotation
    text_content += "--- Redo logs ---\n"
    ret_val = db.redo_test()
    text_content += "%s\n" % ret_val["txt"]
    html_content += render_table("Redo logs", "Max rotacja redo logów:", dbs["db"], ret_val["html"], "redo")
    
    # Check lob partitions
    if lob_check:
        text_content += "--- Lob partitions ---\n"
        ret_val = db.edm_lobs(dbs["db"].upper())
        text_content += "%s\n" % ret_val["txt"]
        html_content += render_table("Lob partitions", "Partycje lob i czas obowiązywania:", dbs["db"], ret_val["html"], "lob")
        if ret_val["alert"] or alert:
            alert = True
            alert_msg += ret_val["alert_msg"]

    # Tablespace size
    text_content += "--- Tablespaces ---\n"
    if multitenant:
        ret_val = db.cdb_tblspc_usage()
    else:
        ret_val = db.tblspc_usage()
    text_content += "%s\n" % ret_val["txt"]
    html_content += render_table("Tablespaces", "Raport przestrzeni tabel:", dbs["db"], ret_val["html"], "tbl")

    # Tables stats
    text_content += "--- Oldest statistics ---\n"
    ret_val = db.stats_test()
    text_content += ret_val["txt"] + "\n"
    html_content += render_table("Oldest statistics", "Raport statystyk tabel:", dbs["db"], ret_val["html"], "stats")

    db.db_connection.close_db()
    results[i] = {}
    results[i]["html"] = html_content
    results[i]["txt"] = text_content
    results[i]["size"] = db_size
    results[i]["alert"] = alert
    results[i]["alert_msg"] = alert_msg
    results[i]["db_version"] = db_version_result
    results[i]["version"] = app_version_result
    results[i]["dbid"] = str(dbid)
    if dataguard:
        results[i]["dataguard"] = dg_status


def main():
    try:
        Utils.parse_params()
        Utils.parse_config_file(configparser)

        if Utils.params["verbose"]:
            logging.getLogger().setLevel(logging.DEBUG)

        global DATE
        global ALERT
        global ALERT_MSG

        template = env.get_template('header.html.j2')
        html_content = template.render(logo=Utils.config["logo"], title=Utils.config["email_title"], report_date=DATE.strftime("%Y-%m-%d"), company=Utils.config['company'])
        txt_content = "%s raport z dnia %s\n" % (Utils.config["email_title"], DATE.strftime("%Y-%m-%d"))

        threads = []
        results = [None] * len(Utils.config["oracle_dbs"])
        
        for i, dbs in enumerate(Utils.config["oracle_dbs"]):
            logs_check = False
            if dbs["db"] in Utils.config["logs_check"]:
                logs_check = True
            
            # app version check according to config file
            version_check = False
            if dbs["db"] in Utils.config["app_amms"]:
                version_check = "amms"
            if dbs["db"] in Utils.config["app_im"]:
                version_check = "im"
            if dbs["db"] in Utils.config["app_docker"]:
                version_check = "docker"

            # edm lobs
            lob_check = False
            if dbs["db"] in Utils.config["app_edm"]:
                lob_check = True

            # multitenancy
            multitenancy = dbs["multitenant"]

            # dataguard
            dataguard = dbs["dataguard"]

            t = threading.Thread(target=db_test, args=(dbs, results, i, logs_check, version_check,
                                                       lob_check, multitenancy, dataguard))
            t.start()
            threads.append(t)
        for t in threads:
            t.join()

        # Database boxes

        j = 0
        jmax = len(Utils.config["oracle_dbs"])
        for i, dbs in enumerate(Utils.config["oracle_dbs"]):
            j += 1
            if j == 1:
                html_content += "<tr>\n<td width=\"350\">\n"

            template = env.get_template('toc.html.j2')
            if dataguard:
                html_content += template.render(dbname=dbs["db"], size=results[i]['size'], alert=results[i]['alert'],
                                                dbid=results[i]['dbid'], version=results[i]['version'],
                                                dg_status=results[i]['dataguard'])
            else:
                html_content += template.render(dbname=dbs["db"], size=results[i]['size'], alert=results[i]['alert'],
                                                dbid=results[i]['dbid'], version=results[i]['version'])
            if ALERT or results[i]['alert']:
                ALERT = True
                ALERT_MSG += results[i]['alert_msg']
            if j == jmax:
                html_content += "</td>\n</tr>\n"
                continue
            if j % 2:
                html_content += "</td>\n<td width=\"350\">\n"
                continue
            elif j < jmax:
                html_content += "</td>\n</tr>\n<tr>\n<td width=\"350\">\n"
                continue

        html_content += "<tr><td>%WARNING_MSG%</td></tr>"
        txt_content += "%WARNING_MSG%"
        
        # Disk usage
        txt_content += "\n=== Database disk usage ====\n"
        template = env.get_template('disk_usage.html.j2')
        if Utils.config["oradata"][0] == "asm": 
            dsk_usage = asm_df(Utils.config["oracle_dbs"][0])
        else:
            dsk_usage = fs_df(Utils.config_host["fs_check"])       
        html_content += template.render(inner_table=dsk_usage["html"], disk_type=Utils.config["oradata"][0])
        txt_content += "\n%s" % dsk_usage["txt"]

        # dbs reports
        for res in results:
            if res is not None:
                html_content += res["html"]
                txt_content += "\n" + res["txt"]

        # Footer

        template = env.get_template('footer.html.j2')
        html_content += template.render(version=__ver__, company="%s (%s)" % (Utils.config['company'], DATE.strftime("%Y")))

        # End TXT
        txt_content += "\n(C) %s (%s), Backup report version %s\n" % (Utils.config['company'], DATE.strftime("%Y"),__ver__)

        html_content = html_content.replace("%WARNING_MSG%", ALERT_MSG)
        txt_content = txt_content.replace("%WARNING_MSG%", ALERT_MSG)

        if Utils.params["verbose"]:
            # print(html_content)
            print(txt_content)
        else:
            email = EmailCreation(ALERT)
            email.create_email(html_content, txt_content)

    except Exception as error:
        logging.warning(str(error))
        raise


if __name__ == "__main__":
    main()

