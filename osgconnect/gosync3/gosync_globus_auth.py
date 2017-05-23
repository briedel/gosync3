#!/usr/bin/env python
import argparse
import logging as log
from globus_db_v2 import globus_db
from connect_db_v2 import connect_db_json as connect_db
from util import parse_json_config


def main(args):
    config = parse_json_config(args.config)
    connectdb = connect_db(config=config)
    globusdb = globus_db(config=config, connect_db=connectdb)
    globus_groups = globusdb.get_all_groups(get_summary=True)
    if len(connectdb.groups.keys()) != len(globus_groups):
        new_groups = [grp for grp in globus_groups
                      if grp["name"] not in connectdb.groups.keys()]
        for ng in new_groups:
            connectdb.add_group(ng)
    for ggrp in globus_groups:
        connectdb.update_group(ggrp)
    globus_members = globusdb.get_all_users(get_user_groups=True)
    if len(connectdb.users.keys()) != len(globus_members):
        new_users = [user for user in globus_members
                     if user["username"] not in connectdb.users.keys()]
        for nu in new_users:
            connectdb.add_user(nu)
    for gusr in globus_members:
        connectdb.update_user(gusr)
    connectdb.write_db()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", help="echo the string you use here",
                        default="gosync3.json")
    args = parser.parse_args()
    log.debug("Using config file %s", args.config)
    main(args)