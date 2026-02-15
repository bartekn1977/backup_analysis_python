# -*- coding: utf-8 -*-
import cx_Oracle
import logging
import datetime
import os
import sys

logger = logging.getLogger(__name__)


class DatabaseUsage(object):

    connection = None

    def __init__(self, db):
        self._connect_db(db)

    def _connect_db(self, db):
        """Connect to database
        """
        try:
            logger.info("Connecting to database: " + db["db"].upper())
            if db["url"] is not None:
                if os.getenv("TNS_ADMIN") is not None:
                    self.connection = cx_Oracle.connect(dsn=db["db"], encoding="UTF-8", nencoding="UTF-8", mode=(cx_Oracle.SYSDBA if db["sysdba"] else cx_Oracle.DEFAULT_AUTH))
                else:
                    self.connection = cx_Oracle.connect(db["url"], encoding="UTF-8", nencoding="UTF-8", mode=(cx_Oracle.SYSDBA if db["sysdba"] else cx_Oracle.DEFAULT_AUTH))
            else:
                raise Exception("No URL")
        except cx_Oracle.DatabaseError as exc:
            error, = exc.args
            logger.warning("Oracle-Error-Code: " + str(error.code))
            logger.warning("Oracle-Error-Message: " + str(error))
            print("Oracle error: " + str(error))
            sys.exit(error.code)

    def close_db(self):
        """Close database connection
        """
        if self.connection is not None:
            self.connection.close()

    def execute_query(self, sql, params=None):
        """Execute SQL query
        """
        try:
            cur = self.connection.cursor()
            if params is not None:
                cur.prepare(sql)
                cur.execute(None, params)
            else:
                cur.execute(sql)
            res = cur.fetchall()
            cur.close()
            return res
        except cx_Oracle.DatabaseError as exc:
            error, = exc.args
            logger.warning("Oracle-Error-Code: " + str(error.code))
            logger.warning("Oracle-Error-Message: " + str(error))

