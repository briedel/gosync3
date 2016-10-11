#!/usr/bin/env python
from __future__ import print_function
import os
import logging
import sqlite3

from optparse import OptionParser

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M')

parser = OptionParser()
parser.add_option("--dbfile", dest="db_filename", default="spt_data_management.db",
                  help="Filename for sqlite3 DB", metavar="FILE")
parser.add_option("--schemafile", dest="db_schema_filename", default="spt_data_management_schema.sql",
                  help="Filename for DB schema file")
parser.add_option("--newDB", action="store_true", dest="new_DB", default=False,
                  help="Completely new DB")
parser.add_option("--pole", action="store_false", dest="pole",
                  help="Assuming we are using the pole setup. More checks: Disk size, disk space, etc.")
(options, args) = parser.parse_args()

def main():
    if os.path.exists(options.db_filename) and not options.new_DB:
        logging.info('Database exists, assume schema does, too.')
    else:
        if os.path.exists(options.db_filename):
            os.remove(options.db_filename)
        with sqlite3.connect(options.db_filename) as conn:    
            logging.info("DB is new")
            with open(options.db_schema_filename, 'rt') as f:
                schema = f.read()
            conn.executescript(schema)

if __name__ == "__main__":
    main()
