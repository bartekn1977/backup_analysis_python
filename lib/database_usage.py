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
            mode = oracledb.SYSDBA if db["sysdba"] else None
            
            # Check if TNS_ADMIN is set (indicates wallet usage)
            if os.getenv("TNS_ADMIN") is not None:
                logger.info("Using Oracle Wallet from TNS_ADMIN: " + os.getenv("TNS_ADMIN"))
                # For wallet-based authentication, use DSN without credentials
                self.connection = oracledb.connect(dsn=db["db"], mode=mode)
            elif db["url"] is not None:
                # Traditional connection with username/password
                self.connection = oracledb.connect(db["url"], mode=mode)
            else:
                raise ValueError("No connection method available: no URL and no TNS_ADMIN")
        except oracledb.DatabaseError as exc:
            error_obj = exc.args[0]
            logger.warning("Oracle-Error-Code: " + str(error_obj.code))
            logger.warning("Oracle-Error-Message: " + str(error_obj))
            print("Oracle error: " + str(error_obj))
            sys.exit(error_obj.code)

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

