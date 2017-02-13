#!/usr/bin/env python
from __future__ import print_function
import argparse
# import psycopg2
import logging as log
from  .. import gosync
from ..gosync.connect_db import connect_users
from globus_db import globus_db_hybrid as globus_db
from util import parse_config, generate_groupid


def main(opts):
    config = parse_config(opts.config)
    log.debug("Config is %s", config)
    if opts.filters is not None:
        config["groups"]["filter_prefix"] = opts.filters
    go_db = globus_db(config)
    print(go_db.get_groups(filters_top_group="osg")["connect"]["osg"])
    print(go_db.get_groups(filters_top_group="spt")["connect"]["spt"])
    # print(go_db.get_groups(filters_prefix="spt"))
    # groups = go_db.get_groups(filters_prefix="spt")
    # for group in groups:
    #     print(group)
    #     print(go_db.get_group_summary(group))
    #     print("------")
    #     if group["name"] == "connect":
    #         continue
    #     summary = go_db.get_group_summary(group)
    #     convert_group_info_go_db(group, summary)
    # group_members, member_group = go_db.get_globus_group_members(
    #     no_top_level=True)
    # current_users = connect_users(config, options)
    # users_work_on = get_users_to_work_on(options, config,
    #                                      member_group, current_users)
    # work_on_users(options, config, users_work_on, current_users)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", dest="config", default="gosync.conf",
                        help="config file to use",)
    opts = parser.parse_args()
    level = {
        1: log.ERROR,
        2: log.WARNING,
        3: log.INFO,
        4: log.DEBUG
    }.get(opts.verbosity, log.DEBUG)
    log.basicConfig(level=level)
    main(opts)
