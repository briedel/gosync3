#!/usr/bin/env python
from __future__ import print_function
import argparse
import json
from globus_db_v2 import globus_db

from util import parse_json_config


def main(args):
    config = parse_json_config(args.config)
    globusdb = globus_db(config=config)
    print(globusdb.get_user_groups("connect"))
    print(globusdb.get_user_groups("briedel"))
    print(globusdb.get_group_tree())
    print(globusdb.get_user_info("nwhitehorn"))
    print(globusdb.get_groups())
    globus_groups = globusdb.get_groups()
    group_name = [g["name"] for g in globus_groups.data]
    print(group_name)
    # with open("globus_groups.json", "w") as gpf:
    #     json.dump(group_name, gpf)
    members = globusdb.get_group_members(
        config["globus"]["groups"]["root_group_uuid"], get_user_summary=True)

    # print(members[0])
    usernames = {member["username"]: member for member in members}
    with open("globus_members.json", "w") as mf:
        json.dump(usernames, mf)
    # print()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", help="echo the string you use here",
                        default="gosync3.json")
    args = parser.parse_args()
    main(args)
