#!/usr/bin/env python
from __future__ import print_function
import argparse
from globus_db_v2 import globus_db

from util import parse_json_config


def main(args):
    config = parse_json_config(args.config)
    globusdb = globus_db(config=config)
    print(globusdb.get_user_groups_membership("connect"))
    print(globusdb.get_user_groups_membership("briedel"))
    print(globusdb.get_group_tree())
    print(globusdb.get_user_info("nwhitehorn"))
    print(globusdb.get_groups())
    # print()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", help="echo the string you use here")
    args = parser.parse_args()
    main(args)
