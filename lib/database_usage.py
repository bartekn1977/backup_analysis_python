import oracledb
import logging
import datetime
import os
import sys

logger = logging.getLogger(__name__)


class DatabaseUsage(object):

    connection = None
    _thick_mode_initialized = False

    def __init__(self, db):
        self._connect_db(db)

    @classmethod
    def _initialize_thick_mode(cls):
        """Initialize oracledb in Thick mode if not already done"""
        if cls._thick_mode_initialized:
            return
            
        oracle_home = os.getenv("ORACLE_HOME")
        if oracle_home and os.getenv("TNS_ADMIN"):
            try:
                # Initialize Thick mode for Oracle Wallet support
                lib_dir = os.path.join(oracle_home, "lib")
                if not os.path.exists(lib_dir):
                    # Try Windows path
                    lib_dir = os.path.join(oracle_home, "bin")
                
                if os.path.exists(lib_dir):
                    oracledb.init_oracle_client(lib_dir=lib_dir)
                    logger.info(f"Initialized oracledb in Thick mode from: {lib_dir}")
                    cls._thick_mode_initialized = True
                else:
                    logger.warning(f"Oracle Client library directory not found: {lib_dir}")
            except Exception as e:
                logger.warning(f"Could not initialize Thick mode: {str(e)}. Using Thin mode.")

    def _connect_db(self, db):
        """Connect to database
        """
        try:
            # Initialize Thick mode if needed (for Oracle Wallet support)
            self._initialize_thick_mode()
            
            logger.info("Connecting to database: " + db["db"].upper())
            mode = oracledb.SYSDBA if db["sysdba"] else None
            
            # Check if TNS_ADMIN is set (indicates wallet usage)
            tns_admin = os.getenv("TNS_ADMIN")
            if tns_admin is not None:
                logger.info("Using Oracle Wallet from TNS_ADMIN: " + tns_admin)
                
                # In Thick mode, TNS_ADMIN is automatically used
                # Connect using just the DSN (TNS alias) - wallet provides credentials
                self.connection = oracledb.connect(dsn=db["db"], mode=mode)
                logger.info("Successfully connected using Oracle Wallet")
                
            elif db["url"] is not None:
                # Traditional connection with username/password
                logger.info("Using traditional connection with credentials")
                self.connection = oracledb.connect(db["url"], mode=mode)
            else:
                raise ValueError("No connection method available: no URL and no TNS_ADMIN")
                
        except oracledb.DatabaseError as exc:
            error_obj = exc.args[0]
            logger.warning("Oracle-Error-Code: " + str(error_obj.code))
            logger.warning("Oracle-Error-Message: " + str(error_obj))
            logger.warning("TNS_ADMIN: " + str(os.getenv("TNS_ADMIN")))
            logger.warning("ORACLE_HOME: " + str(os.getenv("ORACLE_HOME")))
            logger.warning("Connection URL: " + str(db.get("url", "None")))
            logger.warning("Connection DSN: " + str(db.get("db", "None")))
            print("Oracle error: " + str(error_obj))
            print("Check log file for detailed connection information")
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

