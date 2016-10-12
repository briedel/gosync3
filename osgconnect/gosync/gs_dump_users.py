#!/usr/bin/env python
from __future__ import print_function
# import os
import sys
import logging

from optparse import OptionParser

from util import *


def main(options, args):
    config = parse_config(options.config)
    client = get_globus_client(config)


if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("--config", dest="config", default="gosync.conf",
                      help="config file to use",)
    parser.add_option("-v", "--verbosity", dest="verbosity",
                      help="Set logging level", default=3)
    parser.add_option("--format", dest="format", default=['html'],
                      action="callback", callback=callback_optparse,
                      help="Output format to use given as a list")
    parser.add_option("-o", "--outfile", dest="outfile", default=None,
                      help="Output file to write things too")
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
    main(options, args)
