#!/usr/bin/env python3
"""
Backup and Tablespace Analysis
for ORACLE databases

ver. 3.21.0
author: Bart!
(C) data4IT, 2026

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
import logging.handlers
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
WARNING_MSG_PLACEHOLDER = "%WARNING_MSG%"
pathname = os.path.abspath(os.path.dirname(sys.argv[0])) + str(os.sep)

# Setup rotating file handler - daily rotation, keep 30 days of logs
log_file = pathname + "log" + str(os.sep) + "backup_analysis.log"
handler = logging.handlers.TimedRotatingFileHandler(
    log_file,
    when='midnight',
    interval=1,
    backupCount=30,
    encoding='utf-8'
)
handler.setFormatter(logging.Formatter(LOG_FORMAT))
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(handler)

DATE = datetime.datetime.now()
logging.info("Report start: %s" % DATE.strftime("%d-%m-%Y"))
env = Environment(loader=FileSystemLoader('%s/templates/' % os.path.dirname(__file__)))

# Add custom Jinja2 filters
env.filters['format_storage'] = Utils.format_storage_size


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
    logging.info("ASM storage usage: %s" % dbs["db"].upper())
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


def get_app_version(db, app_version, db_name):
    """Get application version based on app type"""
    if not app_version:
        return ""
    
    logging.info("Checking %s version %s" % (app_version.upper(), db_name))
    
    if app_version == 'amms':
        ret_val = db.amms_version()
    elif app_version == 'im':
        ret_val = db.im_version()
    elif app_version == 'docker':
        ret_val = db.docker_version()
    else:
        return ""
    
    return ret_val['version']


def get_database_info(db, dbs, multitenant, dataguard):
    """Get database version, DBID, and DataGuard status"""
    info = {}
    
    # Database version
    ret_val = db.db_version()
    info['db_version'] = ret_val['version']
    logging.info("%s ver.: %s" % (dbs["db"].upper(), info['db_version']))
    
    # DBID for RMAN
    ret_val = db.dbid()
    info['dbid'] = ret_val["dbid"]
    logging.info("%s DBID %s" % (dbs["db"].upper(), str(info['dbid'])))
    
    # DataGuard status
    info['dg_status'] = Utils.get_dg_status(dbs["db"]) if dataguard else None
    
    # PDBs for multitenant
    info['pdb_val'] = db.pdbs() if multitenant else None
    
    return info


def render_db_title(dbs, dbid, db_version, check_logs, lob_check, dg_status, multitenant, pdb_val):
    """Render database title section (HTML and text)"""
    if multitenant:
        template = env.get_template('db_title_cdb.html.j2')
        html_content = template.render(
            dbname=dbs["db"], dbid=dbid, check_logs=check_logs, 
            lob_check=lob_check, pdb_val=pdb_val, 
            dg_status=dg_status, db_version=db_version
        )
        text_content = "=== Database: %s (DBID: %s, ver.: %s) ===\n\n" % (dbs["db"].upper(), dbid, db_version)
        if dg_status:
            text_content += " DataGuard status: {0:}\n".format(dg_status)
        for pdb in pdb_val:
            text_content += " * {0:} ({1:})\n".format(pdb['pdb'], pdb['guid'])
    else:
        template = env.get_template('db_title.html.j2')
        html_content = template.render(
            dbname=dbs["db"], dbid=dbid, check_logs=check_logs,
            lob_check=lob_check, dg_status=dg_status, db_version=db_version
        )
        text_content = "=== Database: %s (DBID: %s, ver.: %s) ===\n\n" % (dbs["db"].upper(), dbid, db_version)
        if dg_status:
            text_content += " DataGuard status: {0:}\n".format(dg_status)
    
    return html_content, text_content


def run_backup_tests(db, dbs, html_content, text_content):
    """Run backup-related tests (FRA, Full, Archive)"""
    alert = False
    alert_msg = ""
    
    # FRA usage
    text_content += "--- Fast Recovery Area ---\n"
    ret_val = db.fra_usage()
    text_content += "%s\n" % ret_val["txt"]
    html_content += render_table("Fast Recovery Area", "Raport zajętość Fast Recovery Area:", 
                                  dbs["db"], ret_val["html"], "fra")
    
    # Full backup
    text_content += "--- Full backup ---\n"
    ret_val = db.full_bck(dbs["db"].upper())
    text_content += "%s\n" % ret_val["txt"]
    html_content += render_table("Full backup", "Raport wykonania kopii pełnych:", 
                                  dbs["db"], ret_val["html"], "full")
    if ret_val["alert"]:
        alert = True
        alert_msg += ret_val["alert_msg"]
    
    # Archivelog backup
    text_content += "--- Archivelog ---\n"
    ret_val = db.arch_bck(dbs["db"].upper())
    text_content += "%s\n" % ret_val["txt"]
    html_content += render_table("Archivelog", "Raport wykonania kopii archive-logów:", 
                                  dbs["db"], ret_val["html"], "arch")
    if ret_val["alert"]:
        alert = True
        alert_msg += ret_val["alert_msg"]
    
    return html_content, text_content, alert, alert_msg


def run_optional_tests(db, dbs, html_content, text_content, check_logs, app_version, lob_check):
    """Run optional tests (logs, certs, lobs)"""
    alert = False
    alert_msg = ""
    
    # Logs stats
    if check_logs:
        text_content += "--- Logs info ---\n"
        ret_val = db.logs_test()
        text_content += "%s\n" % ret_val["txt"]
        html_content += render_table("Logs info", "Raport z migracji logów aplikacji:", 
                                      dbs["db"], ret_val["html"], "logs")
    
    # AMMS certs
    if app_version == 'amms':
        text_content += "--- AMMS Certs ---\n"
        ret_val = db.amms_infra_certs()
        text_content += "%s\n" % ret_val["txt"]
        html_content += render_table("AMMS cert", "Informacje o certyfikatach AMMS:", 
                                      dbs["db"], ret_val["html"], "cert")
    
    # Redo rotation
    text_content += "--- Redo logs ---\n"
    ret_val = db.redo_test()
    text_content += "%s\n" % ret_val["txt"]
    html_content += render_table("Redo logs", "Max rotacja redo logów:", 
                                  dbs["db"], ret_val["html"], "redo")
    
    # Check lob partitions
    if lob_check:
        text_content += "--- Lob partitions ---\n"
        ret_val = db.edm_lobs(dbs["db"].upper())
        text_content += "%s\n" % ret_val["txt"]
        html_content += render_table("Lob partitions", "Partycje lob i czas obowiązywania:", 
                                      dbs["db"], ret_val["html"], "lob")
        if ret_val["alert"]:
            alert = True
            alert_msg += ret_val["alert_msg"]
    
    return html_content, text_content, alert, alert_msg


def run_tablespace_and_stats_tests(db, dbs, html_content, text_content, multitenant):
    """Run tablespace and statistics tests"""
    # Tablespace size
    text_content += "--- Tablespaces ---\n"
    if multitenant:
        logging.info("Using CDB tablespace test for %s (multitenant=True)" % dbs["db"].upper())
        ret_val = db.cdb_tblspc_usage()
    else:
        logging.info("Using standard tablespace test for %s (multitenant=False)" % dbs["db"].upper())
        ret_val = db.tblspc_usage()
    text_content += "%s\n" % ret_val["txt"]
    html_content += render_table("Tablespaces", "Raport przestrzeni tabel:", 
                                  dbs["db"], ret_val["html"], "tbl")
    
    # Tables stats
    text_content += "--- Oldest statistics ---\n"
    ret_val = db.stats_test()
    text_content += ret_val["txt"] + "\n"
    html_content += render_table("Oldest statistics", "Raport statystyk tabel:", 
                                  dbs["db"], ret_val["html"], "stats")
    
    return html_content, text_content


def get_database_size(db, dbs, text_content, multitenant):
    """Get database size and update text content"""
    if multitenant:
        logging.debug("Using CDB size query for %s" % dbs["db"].upper())
        ret_val = db.cdb_db_size()
    else:
        logging.debug("Using standard size query for %s" % dbs["db"].upper())
        ret_val = db.db_size()
    
    text_content += "%s\n" % ret_val["txt"]
    db_size = ret_val["size"]
    logging.info("Database size " + dbs["db"].upper() + " " + str(db_size))
    
    return db_size, text_content


def db_test(dbs, results, i, check_logs=False, app_version=False, lob_check=False,
            multitenant=False, dataguard=False):
    """Execute tests on database"""
    db = DatabaseTests(dbs)
    logging.info("Executing on %s" % dbs["db"].upper())
    
    # Get database information
    db_info = get_database_info(db, dbs, multitenant, dataguard)
    
    # Get app version
    app_version_result = get_app_version(db, app_version, dbs["db"].upper())
    
    # Render DB Title
    html_content, text_content = render_db_title(
        dbs, db_info['dbid'], db_info['db_version'], check_logs, lob_check, 
        db_info['dg_status'], multitenant, db_info['pdb_val']
    )
    
    # Get database size
    db_size, text_content = get_database_size(db, dbs, text_content, multitenant)
    
    # Run backup tests
    html_content, text_content, alert, alert_msg = run_backup_tests(db, dbs, html_content, text_content)
    
    # Run optional tests
    html_opt, text_opt, alert_opt, alert_msg_opt = run_optional_tests(
        db, dbs, html_content, text_content, check_logs, app_version, lob_check
    )
    html_content = html_opt
    text_content = text_opt
    alert = alert or alert_opt
    alert_msg += alert_msg_opt
    
    # Run tablespace and statistics tests
    html_content, text_content = run_tablespace_and_stats_tests(db, dbs, html_content, text_content, multitenant)
    
    # Store results
    db.db_connection.close_db()
    results[i] = {
        "html": html_content,
        "txt": text_content,
        "size": db_size,
        "alert": alert,
        "alert_msg": alert_msg,
        "db_version": db_info['db_version'],
        "version": app_version_result,
        "dbid": str(db_info['dbid'])
    }
    
    if dataguard:
        results[i]["dataguard"] = db_info['dg_status']


def determine_check_flags(dbs, config):
    """Determine which checks to run for a database"""
    flags = {
        'logs_check': dbs["db"] in config.get("logs_check", []),
        'version_check': False,
        'lob_check': dbs["db"] in config.get("app_edm", []),
        'multitenancy': dbs.get("multitenant", False),
        'dataguard': dbs.get("dataguard", False)
    }
    
    # Log multitenancy flag for debugging
    logging.debug("Database %s: multitenant flag = %s (type: %s)" % 
                  (dbs["db"], dbs.get("multitenant", False), type(dbs.get("multitenant", False))))
    
    # Determine app version check
    if dbs["db"] in config.get("app_amms", []):
        flags['version_check'] = "amms"
    elif dbs["db"] in config.get("app_im", []):
        flags['version_check'] = "im"
    elif dbs["db"] in config.get("app_docker", []):
        flags['version_check'] = "docker"
    
    return flags


def run_database_tests_threaded(oracle_dbs, config):
    """Run database tests in parallel threads"""
    threads = []
    results = [None] * len(oracle_dbs)
    
    for i, dbs in enumerate(oracle_dbs):
        flags = determine_check_flags(dbs, config)
        
        t = threading.Thread(
            target=db_test,
            args=(dbs, results, i, flags['logs_check'], flags['version_check'],
                  flags['lob_check'], flags['multitenancy'], flags['dataguard'])
        )
        t.start()
        threads.append(t)
    
    # Wait for all threads to complete
    for t in threads:
        t.join()
    
    return results


def render_database_boxes(oracle_dbs, results):
    """Render database summary boxes (TOC)"""
    html_content = '<tr><td colspan="2" style="padding:16px 0;"><h2 style="margin:0 0 12px 0; color:#2d3748; font-size:18px; font-weight:700;">Podsumowanie baz danych</h2></td></tr>\n'
    html_content += '<tr><td colspan="2"><table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">\n'
    
    template = env.get_template('toc.html.j2')
    
    for i, dbs in enumerate(oracle_dbs):
        # Start new row for every 2 databases
        if i % 2 == 0:
            html_content += "<tr>\n"
        
        # Render box with or without dataguard status
        if dbs.get("dataguard") and results[i].get('dataguard'):
            box_html = template.render(
                dbname=dbs["db"], size=results[i]['size'], alert=results[i]['alert'],
                dbid=results[i]['dbid'], version=results[i]['version'],
                db_version=results[i]['db_version'], dg_status=results[i]['dataguard']
            )
        else:
            box_html = template.render(
                dbname=dbs["db"], size=results[i]['size'], alert=results[i]['alert'],
                dbid=results[i]['dbid'], version=results[i]['version'],
                db_version=results[i]['db_version']
            )
        
        html_content += box_html
        
        # Close row after 2 databases or at the end
        if i % 2 == 1 or i == len(oracle_dbs) - 1:
            # If odd number of databases and last one, add empty cell
            if i == len(oracle_dbs) - 1 and i % 2 == 0:
                html_content += '<td style="padding:6px;"></td>\n'
            html_content += "</tr>\n"
    
    html_content += '</table></td></tr>\n'
    return html_content


def check_for_alerts(results):
    """Check all results for alerts and accumulate alert messages"""
    global ALERT, ALERT_MSG
    
    for result in results:
        if result and result['alert']:
            ALERT = True
            ALERT_MSG += result['alert_msg']


def add_disk_usage_section(config, oracle_dbs):
    """Add disk usage section to the report"""
    template = env.get_template('disk_usage.html.j2')
    
    html = ""
    txt = "\n=== Disk usage summary ===\n\n"

    for storage_type in config.get("oradata", []):
        if storage_type.split(":")[1] == "asm":
            db_to_check = storage_type.split(":")[0]
            logging.info("Checking ASM disk usage for %s" % db_to_check)
            db_access = [db for db in oracle_dbs if db["db"] == db_to_check]
            dsk_usage = asm_df(db_access[0])
        else:
            dsk_usage = fs_df(Utils.config_host["fs_check"])
    
        html += template.render(inner_table=dsk_usage["html"], disk_type=storage_type.split(":")[1])
        txt += "\n=== Database disk usage %s ====\n\n%s" % (storage_type.split(":")[1].upper(), dsk_usage["txt"])
    
    return html, txt


def append_database_reports(results):
    """Append all database-specific reports"""
    html_content = ""
    txt_content = ""
    
    for res in results:
        if res is not None:
            html_content += res["html"]
            txt_content += "\n" + res["txt"]
    
    return html_content, txt_content


def initialize_report_content(config):
    """Initialize HTML and text report headers"""
    template = env.get_template('header.html.j2')
    html_content = template.render(
        logo=config["logo"],
        title=config["email_title"],
        report_date=DATE.strftime("%Y-%m-%d"),
        company=config['company']
    )
    txt_content = "%s raport z dnia %s\n" % (config["email_title"], DATE.strftime("%Y-%m-%d"))
    
    return html_content, txt_content


def finalize_report_content(html_content, txt_content, config):
    """Finalize report with footer and warning messages"""
    template = env.get_template('footer.html.j2')
    html_content += template.render(version=__ver__, company="%s (%s)" % (config['company'], DATE.strftime("%Y")))
    
    txt_content += "\n(C) %s (%s), Backup report version %s\n" % (config['company'], DATE.strftime("%Y"), __ver__)
    
    # Replace warning message placeholders
    html_content = html_content.replace(WARNING_MSG_PLACEHOLDER, ALERT_MSG)
    txt_content = txt_content.replace(WARNING_MSG_PLACEHOLDER, ALERT_MSG)
    
    return html_content, txt_content


def main():
    try:
        Utils.parse_params()
        Utils.parse_config_file(configparser)

        if Utils.params["verbose"]:
            logging.getLogger().setLevel(logging.DEBUG)

        # Initialize report content
        html_content, txt_content = initialize_report_content(Utils.config)
        
        # Run database tests in parallel
        results = run_database_tests_threaded(Utils.config["oracle_dbs"], Utils.config)
        
        # Render database summary boxes
        html_content += render_database_boxes(Utils.config["oracle_dbs"], results)
        
        # Check for alerts
        check_for_alerts(results)
        
        # Add warning message placeholder
        html_content += "<tr><td>" + WARNING_MSG_PLACEHOLDER + "</td></tr>"
        txt_content += WARNING_MSG_PLACEHOLDER
        
        # Add disk usage section
        disk_html, disk_txt = add_disk_usage_section(Utils.config, Utils.config["oracle_dbs"])
        html_content += disk_html
        txt_content += disk_txt
        
        # Append database-specific reports
        reports_html, reports_txt = append_database_reports(results)
        html_content += reports_html
        txt_content += reports_txt
        
        # Finalize report content
        html_content, txt_content = finalize_report_content(html_content, txt_content, Utils.config)
        
        # Output or send email
        if Utils.params["verbose"]:
            print(txt_content)
        else:
            email = EmailCreation(ALERT)
            email.create_email(html_content, txt_content)

    except Exception as error:
        logging.warning(str(error))
        raise


if __name__ == "__main__":
    main()

