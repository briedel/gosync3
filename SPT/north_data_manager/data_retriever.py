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
parser.add_option("--config", dest="config_file", default="spt_data_management.db",
                  help="Filename for sqlite3 DB", metavar="FILE")