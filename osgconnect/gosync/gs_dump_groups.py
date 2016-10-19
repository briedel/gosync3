#!/usr/bin/env python
from __future__ import print_function
import logging

from optparse import OptionParser

from util import *


def get_connect_groupinfo(config, options):
    """
    Parse passwd file to see what users were already provisioned

    :param config: Configuration parameters dict()
    :param options: Command line options
    :return: Tuple if lists, where every list is the user information
    """
    with open(groups_filename, "rt") as f:
        group_info = [tuple(line.lstrip("\n").split(":")) for line in f]
    return tuple(group_info)


def generate_groupid(group_name):
    return (hash(group_name) % 4999) + 5000


def get_group_line(options, config, client, group):
    print("here1")
    g_name = "@" + strip_filters(group['name'], filters)
    members = get_globus_group_members(options, config, client, group)
    gid = generate_groupid(g_name)
    group_line = [g_name,
                  "x",
                  str(gid),
                  ",".join(members)]
    return group_line


def write_group_file(options, config, client, groups):
    with open(groups_filename, "wt") as f:
        for g in groups:
            group_line = get_group_line(options, config, client, group)
            f.write(":".join(group_line))


def main(options, args):
    config = parse_config(options.config)
    client = get_globus_client(config)
    print("here3")
    groups_cache = get_groups_globus(client,
                                     ['admin', 'manager'])
    print("here2")
    groups = get_groups(options, groups_cache)
    write_group_file(options, config, client, groups)


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
    parser.add_option("--selector", dest="selector", default="or",
                      help="Selection flag")
    parser.add_option("--filters", dest="filters", default=None,
                      action="callback", callback=callback_optparse,
                      help="Output format to use given as a list")
    (options, args) = parser.parse_args()
    level = {
        1: logging.ERROR,
        2: logging.WARNING,
        3: logging.INFO,
        4: logging.DEBUG
    }.get(options.verbosity, logging.DEBUG)
    main(options, args)
