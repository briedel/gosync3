#!/usr/bin/env python
from __future__ import print_function
import sys
import argparse
import logging as log
from globus_db import globus_db
from connect_db import connect_db_json as connect_db
from util import parse_json_config

assert sys.version_info >= (2, 7), ("You done fucked up. "
                                    "GOSync3 requires Python 2.7 or greater")


def main(args):
    config = parse_json_config(args.config)
    connectdb = connect_db(config=config)
    globusdb = globus_db(config=config, connect_db=connectdb)
    # Get all groups
    globus_groups = globusdb.get_all_groups(get_summary=True)
    # Create new groups if necessary 
    if len(connectdb.groups.keys()) != len(globus_groups):
        new_groups = [grp for grp in globus_groups
                      if grp["name"] not in connectdb.groups.keys()]
        for ng in new_groups:
            log.info("Creating group %s", ng["name"])
            connectdb.add_group(ng)
    # Update group information, mainly number of users
    for ggrp in globus_groups:
        log.debug("Updating group %s", ggrp["name"])
        connectdb.update_group(ggrp)
    # Get all users
    globus_members = globusdb.get_all_users(get_user_groups=True)
    # Create new users if necessary 
    if len(connectdb.users.keys()) != len(globus_members):
        # Get and create new users
        new_users = [user for user in globus_members
                     if (user["username"] not in connectdb.users.keys() and
                         user["groups"] != ["connect"])]
        for nu in new_users:
            log.info("Creating user %s", nu["username"])
            connectdb.add_user(nu)
    # Update user information, mainlt
    for gusr in globus_members:
        log.debug("Updating user %s", gusr["username"])
        connectdb.update_user(gusr)
    connectdb.write_db()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", help="echo the string you use here",
                        default="gosync3.json")
    parser.add_argument('--verbose', '-v', action='count')
    parser.parse_args(['-vvv'])
    args = parser.parse_args()
    log.basicConfig(format='%(asctime)s %(levelname)s %(message)s',
                    level=args.verbose)
    log.debug("Using config file %s", args.config)
    main(args)
