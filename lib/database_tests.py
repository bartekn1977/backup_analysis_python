import re
from jinja2 import Environment, FileSystemLoader
import os
import sys
from .database_usage import DatabaseUsage
from .utils import Utils
import logging
import datetime

logger = logging.getLogger(__name__)


class DatabaseTests(object):

    db_connection = None  # type: DatabaseUsage
    env = None
    
    # Alert constants
    ALERT_PREFIX = "<p>&raquo; "
    
    # Table header constants - Polish
    HDR_WOLNE_PCT = "Wolne [%]"
    HDR_WOLNE_MB = "Wolne [MB]"
    HDR_RAZEM_MB = "Razem [MB]"
    HDR_UZYCIE_MB = "Użyte [MB]"
    HDR_TABLESPACE = "Przestrzeń tabel"
    HDR_ILOSC_PLIKOW = "Ilość plików"
    HDR_MAX_MB = "Max [MB]"
    HDR_FIZYCZNE_GB = "Physical disk consumption [GB]"
    HDR_DANE_GB = "Space used by data [GB]"
    HDR_PRZYDZIELONE_GB = "Przydzielone miejsce [GB]"
    HDR_SGA_GB = "SGA [GB]"
    HDR_PGA_GB = "PGA [GB]"
    
    # Table header constants - English
    HDR_FREE_PCT = "Free [%]"
    HDR_FREE_MB = "Free [MB]"
    HDR_TOTAL_MB = "Total [MB]"
    HDR_USED_MB = "Used [MB]"
    HDR_TABLESPACE_NAME = "Tablespace name"
    HDR_NUM_FILES = "Number of files"
    HDR_MAX_SPACE_MB = "Max space [MB]"
    
    # Version and date constants
    LBL_AMMS_VERSION = "AMMS version"
    LBL_APP_VERSION = "App version"
    LBL_INSTALL_DATE = "Install date"
    LBL_DATABASE_VERSION = "Database version"

    def __init__(self, db):
        self.env = Environment(loader=FileSystemLoader('%s/sql/' % os.path.dirname(__file__)))
        self.db_connection = DatabaseUsage(db)

    def arch_bck(self, db_name):
        """Get ArchiveLog backup information
        """
        logger.debug("Archivelog Backup test")
        ret_val = {}
        sql_template = self.env.get_template('archivelog_backup.sql')
        sql = sql_template.render()
        result = self.db_connection.execute_query(
            sql, {"period": Utils.config["period"]})
        if len(result) > 0:
            ret_val["html"] = Utils.create_html_table(result, ["Start", "Koniec", "Wejście [MB]", "Wyjście [MB]", "Typ", "Urządzenie", "Status"], style_class="full_tbl", caption="Archivelog backup")
            ret_val["txt"] = Utils.create_txt_table(result, ["Start time", "End time", "Data input", "Data output", "Backup type", "Backup dev", "Status"])
            ret_val['alert'] = False
            ret_val['alert_msg'] = ""
        else:
            ret_val['alert'] = True
            ret_val['alert_msg'] = self.ALERT_PREFIX + db_name + " ARCH Backup missing</p>"
            logger.warning(db_name + " ARCH Backup missing")
            ret_val["html"] = "<h4 style='color:red'>UWAGA! Brak kopii w ramach ostatnich {0:} dni</h4>"\
                .format(str(Utils.config["period"]))
            ret_val["txt"] = "UWAGA! Brak kopii w ramach ostatnich {0:} dni".format(
                str(Utils.config["period"]))
        return ret_val

    def full_bck(self, db_name):
        """Get FULL backup information
        """
        logger.debug("FULL Backup test")
        ret_val = {}
        sql_template = self.env.get_template('full_backup.sql')
        sql = sql_template.render()
        result = self.db_connection.execute_query(
            sql, {"period": Utils.config["period"]})
        if len(result) > 0:
            ret_val["html"] = Utils.create_html_table(result, ["Start", "Koniec", "Wejście [GB]", "Wyjście [GB]",
                                                               "Typ", "Urządzenie", "Status"], style_class="full_tbl",
                                                      caption="Full backup")
            ret_val["txt"] = Utils.create_txt_table(result, ["Start time", "End time", "Data input", "Data output",
                                                             "Backup type", "Backup dev", "Status"])
            ret_val['alert'] = False
            ret_val['alert_msg'] = ""
        else:
            ret_val['alert'] = True
            ret_val['alert_msg'] = self.ALERT_PREFIX + db_name + " FULL Backup missing</p>"
            logger.warning(db_name + " FULL Backup missing")
            ret_val["html"] = "<h4 style='color:red'>UWAGA! Brak kopii w ramach ostatnich {0:} dni</h4>" \
                .format(str(Utils.config["period"]))
            ret_val["txt"] = "UWAGA! Brak kopii w ramach ostatnich {0:} dni".format(
                str(Utils.config["period"]))
        return ret_val

    def pdbs(self):
        """Get PDB list with GUIDs
        """
        logger.debug("PDBs test")
        ret_val = []
        sql_template = self.env.get_template('pdbs.sql')
        sql = sql_template.render()
        result = self.db_connection.execute_query(sql)
        if len(result) > 0:
            for item in result:
                element = {'pdb': item[0], 'guid': item[1]}
                ret_val.append(element)
        else:
            ret_val[0] = None
        return ret_val

    def tblspc_usage(self):
        """Tablespace usage
        """
        logger.debug("Tablespace size test")
        ret_val = {}
        sql_template = self.env.get_template('tablespace_usage.sql')
        sql = sql_template.render()
        result = self.db_connection.execute_query(sql)
        ret_val["html"] = Utils.create_html_table(
            result, 
            [self.HDR_TABLESPACE, self.HDR_ILOSC_PLIKOW, self.HDR_UZYCIE_MB,
             self.HDR_WOLNE_MB, self.HDR_RAZEM_MB, self.HDR_WOLNE_PCT, self.HDR_MAX_MB],
            index_to_test=5, style_class="full_tbl", caption="Tablespaces"
        )
        ret_val["txt"] = Utils.create_txt_table(
            result, 
            [self.HDR_TABLESPACE_NAME, self.HDR_NUM_FILES, self.HDR_USED_MB,
             self.HDR_FREE_MB, self.HDR_TOTAL_MB, self.HDR_FREE_PCT, self.HDR_MAX_SPACE_MB]
        )
        return ret_val

    def cdb_tblspc_usage(self):
        """CDB Tablespace usage
        """
        logger.debug("CDB Tablespace size test")
        ret_val = {}
        sql_template = self.env.get_template('cdb_tablespace_usage.sql')
        sql = sql_template.render()
        result = self.db_connection.execute_query(sql)
        ret_val["html"] = Utils.create_html_table(
            result,
            ["Pluggable Database", self.HDR_TABLESPACE, self.HDR_ILOSC_PLIKOW, self.HDR_UZYCIE_MB,
             self.HDR_WOLNE_MB, self.HDR_RAZEM_MB, self.HDR_WOLNE_PCT, self.HDR_MAX_MB],
            index_to_test=6, style_class="full_tbl", caption="Tablespaces"
        )
        ret_val["txt"] = Utils.create_txt_table(
            result,
            ["Pluggable Database", self.HDR_TABLESPACE_NAME, self.HDR_NUM_FILES, self.HDR_USED_MB,
             self.HDR_FREE_MB, self.HDR_TOTAL_MB, self.HDR_FREE_PCT, self.HDR_MAX_SPACE_MB]
        )
        return ret_val

    def stats_test(self):
        logger.debug("TABLE statistics test")
        ret_val = {}
        sql_template = self.env.get_template('table_statistics.sql')
        sql = sql_template.render()
        result = self.db_connection.execute_query(sql)
        ret_val["html"] = Utils.create_html_table(result, ["Tabela", "Właściciel", "Ostation analizowane"],
                                                  style_class="full_tbl", caption="Oldest statistics count")
        ret_val["txt"] = Utils.create_txt_table(
            result, ["Table name", "Owner", "Last analysed"])
        return ret_val

    def db_size(self):
        logger.debug("DB size")
        ret_val = {}
        sql_template = self.env.get_template('database_size.sql')
        sql = sql_template.render()
        result = self.db_connection.execute_query(sql)
        ret_val["html"] = Utils.create_html_table(
            result,
            [self.HDR_FIZYCZNE_GB, self.HDR_DANE_GB],
            style_class="half_tbl", caption="Database size"
        )
        ret_val["size"] = result[0][0]
        ret_val["txt"] = Utils.create_txt_table(
            result,
            [self.HDR_FIZYCZNE_GB, self.HDR_DANE_GB]
        )
        return ret_val
    
    def db_memory(self):
        logger.debug("DB memory delegation")
        ret_val = {}
        sql_template = self.env.get_template('memory.sql')
        sql = sql_template.render()
        result = self.db_connection.execute_query(sql)
        ret_val["html"] = Utils.create_html_table(
            result,
            [self.HDR_SGA_GB, self.HDR_PGA_GB],
            style_class="half_tbl", caption="Database memory"
        )
        ret_val["sga"] = result[0][0]
        ret_val["pga"] = result[0][1]
        ret_val["txt"] = Utils.create_txt_table(
            result,
            [self.HDR_SGA_GB, self.HDR_PGA_GB]
        )
        return ret_val

    def fra_usage(self):
        logger.debug("Fast Recovery Area usage")
        ret_val = {}
        sql_template = self.env.get_template('fra_usage.sql')
        sql = sql_template.render()
        result = self.db_connection.execute_query(sql)
        ret_val["html"] = Utils.create_html_table(
            result,
            [self.HDR_PRZYDZIELONE_GB, self.HDR_WOLNE_PCT],
            style_class="half_tbl", caption="FRA usage"
        )
        ret_val["size"] = result[0][0]
        ret_val["txt"] = Utils.create_txt_table(
            result,
            ["FRA size [GB]", self.HDR_FREE_PCT]
        )
        return ret_val

    def cdb_db_size(self):
        """CDB database size
        """
        logger.debug("CDB size")
        ret_val = {}
        sql_template = self.env.get_template('cdb_database_size.sql')
        sql = sql_template.render()
        result = self.db_connection.execute_query(sql)
        ret_val["html"] = Utils.create_html_table(
            result,
            [self.HDR_FIZYCZNE_GB, self.HDR_DANE_GB],
            style_class="half_tbl", caption="Database size"
        )
        ret_val["size"] = result[0][0]
        ret_val["txt"] = Utils.create_txt_table(
            result,
            [self.HDR_FIZYCZNE_GB, self.HDR_DANE_GB]
        )
        return ret_val

    def logs_test(self):
        logger.debug("LOG_ZAPISY test")
        ret_val = {}
        sql_template = self.env.get_template('log_zapisy_count.sql')
        sql = sql_template.render()
        result = self.db_connection.execute_query(sql)
        ret_val["html"] = Utils.create_html_table(result, ["-", "Aktualne logi, do archiwizacji", "Logi zaarchiwizowane"],
                                                  style_class="full_tbl", caption="Database Logs")
        ret_val["txt"] = Utils.create_txt_table(
            result, ["-", "Logs to be archived", "Logs archived"])
        return ret_val

    def amms_infra_certs(self):
        logger.debug("AMMS_INFRA.CERTS test")
        ret_val = {}
        sql_template = self.env.get_template('amms_infra_certs.sql')
        sql = sql_template.render()
        result = self.db_connection.execute_query(sql)
        ret_val["html"] = Utils.create_html_table(result, ["Moduł", "Plik", "Data zakończenia"],
                                                  style_class="full_tbl", caption="AMMS certs")
        ret_val["txt"] = Utils.create_txt_table(
            result, ["Module", "File", "Expiration"])
        return ret_val

    def redo_test(self):
        logger.debug("Redo Logs test")
        ret_val = {}
        sql_template = self.env.get_template('redo_logs_rotation.sql')
        sql = sql_template.render()
        result = self.db_connection.execute_query(sql)
        ret_val["html"] = Utils.create_html_table(result, ["Max ilosc rotacji redo logów", "Data i godzina"],
                                                  style_class="full_tbl", caption="Redo logs rotation")
        ret_val["txt"] = Utils.create_txt_table(
            result, ["Redo log rotation max", "Date and hour"])
        return ret_val

    def dbid(self):
        logger.debug("DBID test")
        ret_val = {}
        sql = "select dbid from v$database"
        result = self.db_connection.execute_query(sql)
        ret_val["html"] = Utils.create_html_table(
            result,
            ["DBID"],
            style_class="full_tbl", caption=self.LBL_AMMS_VERSION
        )
        ret_val["dbid"] = result[0][0]
        ret_val["txt"] = Utils.create_txt_table(result, ["DBID"])
        return ret_val

    def amms_version(self):
        logger.debug("AMMS version test")
        ret_val = {}
        sql = "select WER_SYS||'.'||WER_INT||'.'||WER_WEW as version, DT_INST as inst_date from sysadm.zainstal_skladnik  where WER_SYS <> 0 and KOD_SKLADN_INST = 'AP_AMMS'"
        result = self.db_connection.execute_query(sql)
        ret_val["html"] = Utils.create_html_table(
            result,
            ["Wersja AMMS", "Data instalacji"],
            style_class="full_tbl", caption=self.LBL_AMMS_VERSION
        )
        ret_val["version"] = result[0][0]
        ret_val["txt"] = Utils.create_txt_table(
            result,
            [self.LBL_AMMS_VERSION, self.LBL_INSTALL_DATE]
        )
        return ret_val

    def im_version(self):
        logger.debug("InfoMedica version test")
        ret_val = {}
        sql = "select distinct WER_SYS||'.'||WER_INT||'.'||WER_WEW as version, DT_INST as inst_date from sysadm.zainstal_skladnik  where WER_SYS <> 0 and KOD_SKLADN_INST in ('AP_LAB','AP_WMD')"
        result = self.db_connection.execute_query(sql)
        ret_val["html"] = Utils.create_html_table(
            result,
            ["Wersja aplikacji", "Data instalacji"],
            style_class="full_tbl", caption=self.LBL_APP_VERSION
        )
        ret_val["version"] = result[0][0]
        ret_val["txt"] = Utils.create_txt_table(
            result,
            [self.LBL_APP_VERSION, self.LBL_INSTALL_DATE]
        )
        return ret_val

    def docker_version(self):
        logger.debug("Docker APP version test")
        ret_val = {}
        sql_template = self.env.get_template('app_docker_version.sql')
        sql = sql_template.render()
        result = self.db_connection.execute_query(sql)
        ret_val["html"] = Utils.create_html_table(
            result,
            ["LP", "Komponent", "Wersja", "Data instlacji"],
            style_class="full_tbl", caption=self.LBL_APP_VERSION
        )
        ret_val["version"] = result[0][2]
        ret_val["txt"] = Utils.create_txt_table(
            result,
            ["No", "Component", "Version", self.LBL_INSTALL_DATE]
        )
        return ret_val

    def db_version(self):
        logger.debug("Database version test")
        ret_val = {}
        
        # Check database version to determine which query to use
        version_check_sql = "select VERSION from product_component_version where PRODUCT like 'Oracle%' and rownum = 1"
        version_result = self.db_connection.execute_query(version_check_sql)
        db_major_version = int(version_result[0][0].split('.')[0])
        
        # Use version_full for Oracle 19c and newer, VERSION for older versions
        if db_major_version >= 19:
            sql = "select product||'('||version_full||')' as db_ver from product_component_version where PRODUCT like 'Oracle%' and rownum = 1"
        else:
            sql = "select * from (select product||'('||VERSION||')' as db_ver from product_component_version where PRODUCT like 'Oracle%') where rownum = 1"
        
        result = self.db_connection.execute_query(sql)
        ret_val["html"] = Utils.create_html_table(
            result,
            ["Wersja bazy danych"],
            style_class="full_tbl", caption=self.LBL_DATABASE_VERSION
        )
        ret_val["version"] = result[0][0]
        ret_val["txt"] = Utils.create_txt_table(result, [self.LBL_DATABASE_VERSION])
        return ret_val

    def edm_lobs(self, db_name):
        logger.debug("EDM LOBs test")
        ret_val = {}
        sql_template = self.env.get_template('app_edm_lob.sql')
        sql = sql_template.render()
        result = self.db_connection.execute_query(sql)
        ret_val["html"] = Utils.create_html_table(result, ["Plik parycji", "Wielkość aktualna [GB]", "Max [GB]", "Data początkowa",
                                                           "Data końcowa", "Lb. dni do konca"], style_class="full_tbl",
                                                  index_to_test=5, caption="LOB partitions")
        ret_val["txt"] = Utils.create_txt_table(result, ["Partition file", "Size [GB]", "Max [GB]", "Start date",
                                                         "End date", "Days left"])
        ret_val['alert'] = False
        ret_val['alert_msg'] = ""
        if result[0][5] <= float(Utils.config["period"])*5:
            ret_val['alert'] = True
            ret_val['alert_msg'] = self.ALERT_PREFIX + db_name + " Należy utworzyć nowe pliki parycji</p>"
            logger.warning(db_name + " add new partition")
            ret_val["html"] = "<h4 style='color:red'>UWAGA! Należy utworzyć nowe pliki parycji, pozostało {0:} dni</h4>" \
                .format(str(round(float(Utils.config["period"])*5)))
            ret_val["txt"] = "UWAGA! Należy utworzyć nowe pliki parycji, pozostało {0:} dni".format(
                str(round(float(Utils.config["period"])*5)))
        return ret_val
