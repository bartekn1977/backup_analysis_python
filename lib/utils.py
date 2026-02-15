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
    def create_html_table(tbl_data, tbl_header, index_to_test=None, style_class="", caption="Data table"):
        """generate HTML table

        :param tbl_data:
        :param tbl_header:
        :param index_to_test:
        :param style_class:
        :param caption
        :return:
        """

        html = "<tr>\n<td width=\"700\">\n"
        html += "<table align=\"left\" border=\"0\" cellpadding=\"0\" cellspacing=\"4\" width=\"100%\"" \
                "style=\"border: 1px solid #a8a8a8; -webkit-border-radius:6px\">\n<tr>\n<thead>\n"
        for header in tbl_header:
            html += "<th style=\"color: #444\">{0:}</th>\n".format(header)
        html += "</tr>\n</thead>\n<tbody>\n"
        for row in tbl_data:
            html += "<tr>\n"
            for col, val in enumerate(row):
                if isinstance(val, (int, long, float)):
                    if index_to_test is not None\
                            and index_to_test == col and float(val) < float(Utils.config["threshold"]):
                        html += "<td style=\"color:#cf0000;font-weight:bold;text-align:right;\">{0:.2f}</td>\n".format(val)
                    else:
                        html += "<td style=\"text-align:right;\">{0:.2f}</td>\n".format(val)
                else:
                    html += "<td>%s</td>\n" % val
            html += "</tr>\n"
        html += "</tbody>\n</table>\n</td>\n</tr>\n"
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
        if sys.version_info >= (3,) or isinstance(path, unicode):
            fun = ctypes.windll.kernel32.GetDiskFreeSpaceExW
        else:
            fun = ctypes.windll.kernel32.GetDiskFreeSpaceExA
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
    def parse_config_file(ConfigParser):
        """Parse config file
        """
        global pathname
        try:
            cfg = ConfigParser.RawConfigParser(allow_no_value=True)
            cfg.read(pathname + Utils.params["config_file"])

            # Oracle part
            orcl_data = cfg.items('oracle')
            for key, val in orcl_data:
                os.environ[key.upper()] = val
                if key in ("oracle_home"):
                    os.environ["PATH"] = val + "/bin:" + os.environ["PATH"]

            # Report part
            config_data = cfg.items('report')
            logger.info("-- Parsing config file: %s%s" % (pathname, Utils.params["config_file"]))
            parsed_config_data = {}
            for key, val in config_data:
                logger.info("%s = %s" % (key, val))

                if key in ("oracle_dbs"):
                    parsed_config_data[key] = []
                    elem_list = val.split(",")
                    elem_list = [item.strip() for item in elem_list]
                    for i in range(len(elem_list)):
                        parsed_config_data[key].append(
                            {"url": elem_list[i], "db": elem_list[i].split("@")[-1]})
                elif key in ("oradata", "logs_check", "app_amms", "app_im", "app_docker", "app_edm"):
                    elem_list = val.split(",")
                    elem_list = [item.strip() for item in elem_list]
                    parsed_config_data[key] = elem_list
                else:
                    parsed_config_data[key] = val

            for item in parsed_config_data["oracle_dbs"]:
                if "use_sysdba" in parsed_config_data:
                    item['sysdba'] = (lambda x: True if x == 'yes' else False)(parsed_config_data["use_sysdba"])
                else:
                    item['sysdba'] = True
                if "multitenant" in parsed_config_data:
                    item['multitenant'] = (lambda x: True if x == 'yes' else False)(parsed_config_data["multitenant"])
                else:
                    item['multitenant'] = False

                if "dataguard" in parsed_config_data:
                    item['dataguard'] = (lambda x: True if x == 'yes' else False)(parsed_config_data["dataguard"])
                else:
                    item['dataguard'] = False

            # Host part
            host_data = cfg.items('host')
            parsed_host_data = {}
            for key, val in host_data:
                if key in ("host_name", "fs_check", "fs_shared"):
                    parsed_host_data[key] = []
                    elem_list = val.split(",")
                    elem_list = [item.strip() for item in elem_list]
                    parsed_host_data[key] = elem_list
            parsed_host_data["current_host"] = os.uname()[1]

            Utils.config = parsed_config_data
            Utils.config_host = parsed_host_data
            logger.info(Utils.config)
            logger.info(Utils.config_host)
            return Utils.config
        except ConfigParser.Error, e:
            logger.warning("Config parse error: %s" % e)
            print("Config parse error %s" % e)
            sys.exit(1)
        except Exception, e:
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
