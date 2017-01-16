#!/usr/bin/env python
from __future__ import print_function
import os
import logging
import sqlite3

from optparse import OptionParser

def main(options, args):
    with sqlite3.connect(options.db_filename) as conn:
        cursor = conn.cursor()
        cursor.execute("""SELECT * FROM disks""")
        results = cursor.fetchall()
        for r in results:
            print(r)

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("--dbfile",
                      dest="db_filename", default="test.db",
                      help="Filename for sqlite3 DB",
                      metavar="FILE")
    (options, args) = parser.parse_args()
    main(options, args)