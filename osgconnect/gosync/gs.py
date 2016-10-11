#!/usr/bin/env python
from future import print_function
import os
import sys
import ConfigParser
import logging
import getopt
import time
import glob
import json
import re
import fnmatch
import errno
import random
import socket
import grp
import pwd

from optparse import OptionParser

from util import *

try:
    from nexus import GlobusOnlineRestClient
except:
    logging.error(("Cannot import Globus Nexus. Trying to "
                   "import Globus SDK Auth Client"))
    try:
        from globus_sdk import AuthClient
    except:
        logging.error(("Cannot import Globus Auth Client "
                       "or Globus Nexus. Exiting"))
        raise RuntimeError()

parser = OptionParser()
parser.add_option("--config", dest="config",
                  help="config file to use",)
parser.add_option("-v", "--verbosity", dest="verbosity",
                  help="Set logging level", default=3)
parser.add_option("--format", dest="format",
                  help="Output format to use")
parser.add_option("--force", dest="force", action="store_true",
                  default=False, help="Force update information")
parser.add_option("--baseurl", dest="baseurl", default=None,
                  help="Base URL to use")
parser.add_option("--portal", dest="portal", default=None,
                  help="Portal to use")
parser.add_option("--parent", dest="parent", default=None,
                  help="Parent group to use")
parser.add_option("--top", dest="top", default=None,
                  help="Top group to use")
parser.add_option("--group", dest="group", default=None,
                  help="Group to use")
parser.add_option("--user", dest="user", default=None,
                  help="User to use")

(options, args) = parser.parse_args()

level = {
    1: logging.ERROR,
    2: logging.WARNING,
    3: logging.INFO,
    4: logging.DEBUG
}.get(options.verbosity, logging.DEBUG)

def main():
    config = parse_config(options.config)
    nexusconfig = {"server": config['globus']['server'],
                   "client": user,
                   "client_secret": self.get(section, 'secret')}
    client = GlobusOnlineRestClient(config=nexusconfig)
    print(client.get_group_list(my_roles=['admin']))

if __name__ == '__main__':
    main()