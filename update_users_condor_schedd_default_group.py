#!/usr/bin/env python
from __future__ import print_function
import sys
import argparse
import logging as log
from connect_db import connect_db_json as connect_db
from util import parse_json_config

import random

assert sys.version_info >= (2, 7), ("You done fucked up. "
                                    "GOSync3 requires Python 2.7 or greater")

def main(args):
    config = parse_json_config(args.config)
    connectdb = connect_db(config=config)
    new_users = {}
    for username, user_info in connectdb.users.iteritems():
        user_info["condor_schedd"] = random.randint(1, 5)
        user_info["connect_project"] = None
        if ["connect"] == user_info["groups"]:
            continue
        new_users[username] = user_info
    connectdb.users = new_users
    connectdb.write_db()
        # print(user_info)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", help="echo the string you use here",
                        default="gosync3.json")
    parser.add_argument('--verbose', '-v', action='count')
    parser.parse_args(['-vvv'])
    args = parser.parse_args()
    log.basicConfig(format='%(asctime)s %(levelname)s %(message)s', level=args.verbose)
    log.debug("Using config file %s", args.config)
    main(args)