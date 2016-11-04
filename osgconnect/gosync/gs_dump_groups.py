#!/usr/bin/env python
from __future__ import print_function
import logging as log
import sys
from optparse import OptionParser
from globus_db import globus_db_nexus as globus_db

from util import *


def get_connect_groupinfo(config, options):
    """
    Parse passwd file to see what users were already provisioned

    :param config: Configuration parameters dict()
    :param options: Command line options
    :return: Tuple if lists, where every list is the user information
    """
    with open(config["groups"]["groups_filename"], "rt") as f:
        group_info = [tuple(line.lstrip("\n").split(":")) for line in f]
    return tuple(group_info)


def generate_groupid(group_name):
    return (hash(group_name) % 4999) + 5000


def get_group_line(options, config, group):
    g_name = "@" + strip_filters(group[0], config["groups"]["filter_prefix"])
    gid = generate_groupid(g_name)
    group_line = [g_name,
                  "x",
                  str(gid),
                  ",".join(group[1]["usernames"])]
    return group_line


def write_group_file(options, config, groups):
    with open(config["groups"]["group_file"], "wt") as f:
        for g in groups.iteritems():
            group_line = get_group_line(options, config, g)
            f.write(":".join(group_line) + "\n")


def main(options, args):
    config = parse_config(options.config)
    log.debug("Config is %s", config)
    if options.filters is not None:
        config["groups"]["filter_prefix"] = options.filters
    go_db = globus_db(config)
    group_members, member_group = go_db.get_globus_group_members(get_user_profile=False,
        no_top_level=True)
    print(group_members.keys())
    write_group_file(options, config, group_members)


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
    parser.add_option("--filters", dest="filters", default=None,
                      action="callback", callback=callback_optparse,
                      help="Output format to use given as a list")
    (options, args) = parser.parse_args()
    level = {
        1: logging.ERROR,
        2: logging.WARNING,
        3: logging.INFO,
        4: logging.DEBUG
    }.get(options.verbosity, log.DEBUG)
    main(options, args)
