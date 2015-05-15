import microbedb.config_singleton
import mysql.connector
from mysql.connector import Error

'''
Module for initializing a connection to the database,
acts like a singleton.

@author: Matthew Laird
@created: May 8, 2015
'''

conn = None

def initDB():

    cfg = microbedb.config_singleton.getConfig()

    try:
        conn = mysql.connector.connect(host=cfg.db_host,
                                       database=cfg.database,
                                       user=cfg.db_user,
                                       password=cfg.db_password)

        if conn.is_connected():
            return conn

    except Error as e:
        print "Error connecting to db: {}".format(str(e))
        raise e

    raise Exception("Error connecting to database, unknown reason")

def fetch_connection():
    global conn

    if conn:
        return self.conn

    raise("Database connection not initialized yet")
