import oracledb
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
                mode = oracledb.SYSDBA if db["sysdba"] else None
                if os.getenv("TNS_ADMIN") is not None:
                    self.connection = oracledb.connect(dsn=db["db"], mode=mode)
                else:
                    self.connection = oracledb.connect(db["url"], mode=mode)
            else:
                raise ValueError("No URL")
        except oracledb.DatabaseError as exc:
            logger.warning("Oracle-Error-Code: " + str(exc.args[0].code))
            logger.warning("Oracle-Error-Message: " + str(exc.args[0]))
            print("Oracle error: " + str(exc.args[0]))
            sys.exit(exc.args[0].code)

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
                cur.execute(sql, params)
            else:
                cur.execute(sql)
            res = cur.fetchall()
            cur.close()
            return res
        except oracledb.DatabaseError as exc:
            logger.warning("Oracle-Error-Code: " + str(exc.args[0].code))
            logger.warning("Oracle-Error-Message: " + str(exc.args[0]))

