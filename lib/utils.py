# -*- coding: utf-8 -*-
from jinja2 import Environment, FileSystemLoader
import os
import sys
from optparse import OptionParser
from optparse import OptionGroup
import logging
import datetime
import texttable
import subprocess
import ctypes
import configparser

__ver__ = "3.17.0"
logger = logging.getLogger(__name__)
pathname = os.path.abspath(os.path.dirname(sys.argv[0])) + str(os.sep)


class Utils(object):

    env = Environment(loader=FileSystemLoader(
        '%s/templates/' % os.path.dirname(__file__)))

    params = {}

    config = {}

    config_host = {}

    help_msg = """\
This script generates Oracle backup and usage report, especially for Asseco based applications
Version """ + __ver__ + """
(C) data4IT 2024
"""

    @staticmethod
    def create_txt_table(tbl_data, tbl_header):
        """generates text table

        :param tbl_data:
        :param tbl_header:
        :return:
        """
        table = texttable.Texttable()
        table.header(tbl_header)
        table.add_rows(tbl_data, header=False)
        return table.draw() + "\n"

    @staticmethod
    def _format_table_cell(val, col, index_to_test):
        """Format a single table cell value"""
        if isinstance(val, (int, float)):
            # Check if value is below threshold
            if index_to_test is not None and index_to_test == col and float(val) < float(Utils.config["threshold"]):
                text_style = 'color:#e53e3e; font-weight:700;'
            else:
                text_style = 'color:#2d3748;'
            return '<td style="{0}text-align:right; padding:6px 8px; font-size:12px;">{1:.2f}</td>\n'.format(text_style, val)
        else:
            return '<td style="color:#4a5568; padding:6px 8px; font-size:12px;">{0:}</td>\n'.format(val)

    @staticmethod
    def create_html_table(tbl_data, tbl_header, index_to_test=None, style_class="", caption="Data table"):
        """generate HTML table with modern email-safe styling

        :param tbl_data:
        :param tbl_header:
        :param index_to_test:
        :param style_class:
        :param caption
        :return:
        """

        html = '<table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="border-collapse:collapse; margin:12px 0;">\n'
        html += '<tr style="background-color:#f7fafc; border-bottom:2px solid #e2e8f0;">\n'
        
        for col, header in enumerate(tbl_header):
            html += '<th style="color:#2d3748; font-weight:700; font-size:12px; text-align:left; padding:6px 8px; text-transform:uppercase; letter-spacing:0.5px;">{0:}</th>\n'.format(header)
        
        html += '</tr>\n'
        
        row_count = 0
        for row in tbl_data:
            bg_color = '#ffffff' if row_count % 2 == 0 else '#f7fafc'
            html += '<tr style="background-color:{0}; border-bottom:1px solid #e2e8f0;">\n'.format(bg_color)
            
            for col, val in enumerate(row):
                html += Utils._format_table_cell(val, col, index_to_test)
            
            html += '</tr>\n'
            row_count += 1
        
        html += '</table>\n'
        return html

    @staticmethod
    def toc(db_name, db_size, db_alert, db_id, app_version=False):
        """Generate Tables of Contents for email
        """

        if app_version:
            app_version_str = "<span style=\"font-size:12px; color:#748080;\"> ({0:}) </span>".format(
                app_version)
        else:
            app_version_str = ""

        html = "<!-- Box {0:} -->\n".format(db_name)

        html += "<table width=\"100%\" cellspacing=\"4\" cellpadding=\"0\" style=\"border: 1px solid #a8a8a8; -webkit-border-radius: 6px\">\n"
        html += "<tr>\n<td align=\"center\" colspan=\"2\">Baza danych:\n"
        html += "<h2 style=\"color: #444\"><img src=\"cid:0\" align=\"bottom\" style=\"border:0px; margin-top:2px;\" alt=\"-\">&nbsp; {0:} {1:}</h2>".format(db_name.upper(), app_version_str)
        html += "<span style=\"font-size:12px; color:#748080;\">DBID: {0:}</span>".format(db_id)
        html += "</td>\n</tr>\n<tr>\n<td width=\"50%\" align=\"center\">\nWielkość [GB]:\n<h3>{0:.2f}</h3>\n</td>\n".format(float(db_size))
        html += "<td width=\"50%\" align=\"center\">Status kopii:"
        if db_alert:
            html += "<h3 style=\"background-color: #880000;color: #fff;\">BŁĄD</h3>\n</td>\n</tr>\n"
        else:
            html += "<h3 style=\"background-color: #349651;color: #fff;\">OK</h3>\n</td>\n</tr>\n"
        html += "<tr>\n<td align=\"center\" colspan=\"2\" style=\"border-top: 1px solid #a8a8a8;\">\n"
        html += "<p style=\"margin:6px;\"><a href=\"#{0:}\">Szczegółowe raporty &raquo;</a></p>".format(db_name.upper())
        html += "</td>\n</tr>\n</table>\n"
        html += "<!-- Box {0:} -->\n".format(db_name)

        return html

    @staticmethod
    def disk_usage_linux(path):
        """
        if hasattr(os, 'statvfs'):  # POSIX
        :param path:
        :return:
        """
        st = os.statvfs(path)
        free = st.f_bavail * st.f_frsize
        total = st.f_blocks * st.f_frsize
        used = (st.f_blocks - st.f_bfree) * st.f_frsize
        return total, used, free

    @staticmethod
    def disk_usage_win(path):
        """
        if os.name == 'nt':       # Windows
        :param path:
        :return:
        """
        _, total, free = ctypes.c_ulonglong(), ctypes.c_ulonglong(), \
            ctypes.c_ulonglong()
        fun = ctypes.windll.kernel32.GetDiskFreeSpaceExW
        ret = fun(path, ctypes.byref(_), ctypes.byref(
            total), ctypes.byref(free))
        if ret == 0:
            raise ctypes.WinError()
        used = total.value - free.value
        return total.value, used, free.value

    @staticmethod
    def get_dg_status(db):
        """
        check DatagUard status from dgmgrl tool
        :param db:
        :return:
        """
        logging.info("Checking DataGuard status for {0:}".format(db))
        dg_env = os.environ.copy()
        dgmgrl = subprocess.Popen(["dgmgrl", "/@" + db], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, universal_newlines=True, bufsize=0, env=dg_env)
        dgmgrl.stdin.write("show configuration lag;\n")
        dgmgrl.stdin.write("exit;\n")
        dgmgrl.stdin.close()

        for line in dgmgrl.stdout:
            if "SUCCESS" in line.strip():
                logger.info(" SUCCESS")
                return "SUCCESS"
            if "ERROR" in line.strip():
                logger.error(" SUCCESS")
                return "ERROR"
            if "WARNING" in line.strip():
                logger.warning(" WARNING")
                return "WARNING"

    @staticmethod
    def get_config():
        return Utils.config

    @staticmethod
    def _parse_oracle_section(cfg):
        """Parse oracle section of config file and set environment variables"""
        orcl_data = cfg.items('oracle')
        for key, val in orcl_data:
            os.environ[key.upper()] = val
            if key == "oracle_home":
                os.environ["PATH"] = val + "/bin:" + os.environ["PATH"]

    @staticmethod
    def _parse_list_config_value(val):
        """Parse comma-separated list from config value"""
        elem_list = val.split(",")
        return [item.strip() for item in elem_list]

    @staticmethod
    def _parse_oracle_dbs_config(val):
        """Parse oracle_dbs configuration value"""
        parsed_dbs = []
        elem_list = Utils._parse_list_config_value(val)
        for elem in elem_list:
            parsed_dbs.append({
                "url": elem,
                "db": elem.split("@")[-1]
            })
        return parsed_dbs

    @staticmethod
    def _add_db_flags_to_oracle_dbs(oracle_dbs, parsed_config_data):
        """Add sysdba, multitenant, and dataguard flags to oracle_dbs entries"""
        for item in oracle_dbs:
            # SYSDBA flag
            sysdba_value = parsed_config_data.get("use_sysdba", "yes")
            item['sysdba'] = str(sysdba_value).strip().lower() == "yes"
            
            # Multitenant flag
            multitenant_value = parsed_config_data.get("multitenant", "no")
            item['multitenant'] = str(multitenant_value).strip().lower() == "yes"
            
            # DataGuard flag
            dataguard_value = parsed_config_data.get("dataguard", "no")
            item['dataguard'] = str(dataguard_value).strip().lower() == "yes"
            
            logger.info("Database %s flags set: sysdba=%s, multitenant=%s, dataguard=%s" % 
                       (item['db'], item['sysdba'], item['multitenant'], item['dataguard']))

    @staticmethod
    def _parse_report_section(cfg):
        """Parse report section of config file"""
        config_data = cfg.items('report')
        logger.info("-- Parsing config file: %s%s" % (pathname, Utils.params["config_file"]))
        parsed_config_data = {}
        
        list_keys = ("oradata", "logs_check", "app_amms", "app_im", "app_docker", "app_edm")
        
        for key, val in config_data:
            logger.info("%s = %s" % (key, val))
            
            if key == "oracle_dbs":
                parsed_config_data[key] = Utils._parse_oracle_dbs_config(val)
            elif key in list_keys:
                parsed_config_data[key] = Utils._parse_list_config_value(val)
            else:
                parsed_config_data[key] = val
        
        # Add flags to oracle_dbs
        if "oracle_dbs" in parsed_config_data:
            Utils._add_db_flags_to_oracle_dbs(parsed_config_data["oracle_dbs"], parsed_config_data)
        
        return parsed_config_data

    @staticmethod
    def _parse_host_section(cfg):
        """Parse host section of config file"""
        host_data = cfg.items('host')
        parsed_host_data = {}
        
        list_keys = ("host_name", "fs_check", "fs_shared")
        
        for key, val in host_data:
            if key in list_keys:
                parsed_host_data[key] = Utils._parse_list_config_value(val)
        
        parsed_host_data["current_host"] = os.uname()[1]
        return parsed_host_data

    @staticmethod
    def parse_config_file(config_parser):
        """Parse config file
        
        :param config_parser: ConfigParser module reference
        """
        global pathname
        try:
            cfg = config_parser.RawConfigParser(allow_no_value=True)
            cfg.read(pathname + Utils.params["config_file"])

            # Parse sections
            Utils._parse_oracle_section(cfg)
            parsed_config_data = Utils._parse_report_section(cfg)
            parsed_host_data = Utils._parse_host_section(cfg)

            # Store results
            Utils.config = parsed_config_data
            Utils.config_host = parsed_host_data
            logger.info(Utils.config)
            logger.info(Utils.config_host)
            return Utils.config
            
        except configparser.Error as e:
            logger.warning("Config parse error: %s" % e)
            print("Config parse error %s" % e)
            sys.exit(1)
        except Exception as e:
            logger.warning(str(e))
            print("Config error %s" % e)
            sys.exit(1)

    @staticmethod
    def get_params():
        return Utils.params

    @staticmethod
    def parse_params():
        parser = OptionParser(usage="%prog [-f] [-v|-q]", version=__ver__, prog="backup_analysis.py",
                              description=Utils.help_msg)
        parser.set_defaults(verbose=False)
        parser.add_option("-v", "--verbose", dest="verbose", help="creates output on console, tables in text format",
                          action="store_true", default=True)
        parser.add_option("-q", "--quiet", dest="verbose",
                          action="store_false", default=False)
        parser.add_option("-f", "--file", dest="config_file", help="read configuration from given file",
                          default="config.cfg")
        (options, args) = parser.parse_args()
        Utils.params["config_file"] = options.config_file
        Utils.params["verbose"] = options.verbose
        logger.info(Utils.params)
