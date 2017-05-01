#!/usr/bin/env python
from __future__ import print_function
import json
import argparse
from collections import defaultdict
from itertools import groupby
from operator import itemgetter
from util import parse_json_config


def invert_dict_list_values(dic):
    return {x: list(t[1] for t in group)
            for (x, group) in groupby(sorted(((j, k) for k, v in dic.items()
                                              for j in v), key=itemgetter(0)),
                                      key=itemgetter(0))
            }


def main(args):
    config = parse_json_config(args.config)
    with open("globus_groups.json", "r") as ggf:
        globus_groups = json.load(ggf)
    osg_groups = [grp.split(".")[-1] for grp in globus_groups if "osg" in grp]
    json_out = {"accounts::groups": {"users": {"gid": 1000}},
                "accounts::users": defaultdict(dict)}
    with open(config["groups"]["group_file"], 'r') as gf:
        groups = json_out["accounts::groups"]
        group_members = {}
        for line in gf:
            line = line.rstrip("\n")
            group = line.split(":")
            gname = group[0].replace("@", "")
            if (gname.split("-")[0] in
                config["globus"]["groups"]["top_level_groups"] and
                gname not in config["globus"]["groups"]["top_level_groups"]):
                if len(gname.split("-")) >= 4:
                    # print("-".join(gname.split("-")[3:]))
                    gname = (".".join(gname.split("-")[0:2]) +
                             "." + "-".join(gname.split("-")[2:]))
                elif (gname.split("-")[0] != "atlas" and
                      gname.split("-")[0] != "cms"):
                    gname = (gname.split("-")[0] + "." +
                             "-".join(gname.split("-")[1:]))
                else:
                    gname = gname.replace("-", ".")
            if gname in globus_groups:
                groups[gname] = {"gid": int(group[2])}
                group_members[gname] = group[-1].split(",")
            elif gname in osg_groups:
                groups["osg." + gname] = {"gid": int(group[2])}
                group_members["osg." + gname] = group[-1].split(",")
            elif gname == "ConnectTrain":
                groups["old.ConnectTrain"] = {"gid": int(group[2])}
                group_members["old.ConnectTrain"] = group[-1].split(",")
    member_groups = invert_dict_list_values(group_members)
    with open("globus_members.json", "r") as gmf:
        globus_members = json.load(gmf)
    with open(config["users"]["passwd_file"], "r") as pf:
        users = json_out["accounts::users"]
        for line in pf:
            line = line.rstrip("\n")
            user_info = line.split(":")
            if user_info[0] not in globus_members:
                continue
            puppet_ssh_key = defaultdict(dict)
            for key in globus_members[user_info[0]]["ssh_pubkeys"]:
                key_pieces = key.split(" ")
                # Question about keys that dont have emails or hostnames
                # What to do????
                if len(key_pieces) > 3:
                    key_pieces = key_pieces[0:2]
                if key_pieces[-1] != "":
                    key_pieces[-1] = key_pieces[-1].splitlines()[0]
                else:
                    key_pieces = key_pieces[:-1]
                if len(key_pieces) == 3:
                    puppet_ssh_key[key_pieces[-1]] = {"type": key_pieces[0],
                                                      "key": key_pieces[1]}
                else:
                    puppet_ssh_key[globus_members[user_info[0]]["email"]] = {
                        "type": key_pieces[0],
                        "key": key_pieces[1]}
            users[user_info[0]] = {
                "comment": globus_members[user_info[0]]["name"],
                "gid": int(user_info[3]),
                "uid": int(user_info[2]),
                "manage_group": False,
                "email": globus_members[user_info[0]]["email"],
                "groups": ([] if user_info[0] not in member_groups.keys()
                           else member_groups[user_info[0]]),
                "shell": user_info[-1],
                "ssh_keys": puppet_ssh_key,
                "nexus_refresh_token": None,
                "auth_refresh_token": None}
    # print(json_out)
    with open("test_groups.json", "w") as jtg:
        json.dump(json_out, jtg)

    # "briedel": {
    #   "comment": "Benedikt Riedel",
    #   "gid": 1000,
    #   "uid": 58068,
    #   "manage_group": false,
    #   "groups": [
    #     "connect",
    #     "icecube",
    #     "spt",
    #     "osg",
    #     "uchicago",
    #     "spt-all",
    #     "SouthPoleTelescope",
    #     "xenon1t"
    #   ],
    #   "shell": "/bin/bash",
    #   "ssh_keys": {
    #     "benedikt.riedel@icecube.wisc.edu": {
    #       "type": "ssh-rsa",
    #       "key": "AAAAB3NzaC1yc2EAAAABIwAAAgEA4S7HFXLheNFj60djZlmCEuQuNbxuSOzmgaokTo+HRO0/WiWWSxFKZpJatCeA00NO8IiVJuQTUZEIv0Z/WWAf/Ct2MAj11IXgJzjsjmj8TmaQrCfstdDe3EPGcSfIS1Mbakh9FZEzt/665EVgCuFAX7fcRWn3zYWwqiLvLl1YljJtqxWsbhDuETc7opK+L0JaS+PJIkq4vsADfmpWP49k2T1xIEoH8L/W1XyrMCXpwd2OvCIm04G2cElDEk40kh30Txwtypr3ABAb/ybp6LxylUVhHpQws5jQ9peIOkft8ciq7wModVyR4M8qazZy0xwSo37y6cdNuK4WkhoUR39Ipoc7CCvE+IkEAiKKFFM7IQcHXXfl9jQaabCbu4UpNxLtmIDYosvKdda0fKh5d6t9BG6P4Hln649w3hejL7fKzqPSb0VMxz7E++0EuI8fUsbTQkQlQjnGYVOyUqDlUV6qAXX00MCnnmHek2mlGT4qi1iUJQvuix3eCPYkjMhBFktxPQ7NwIn7lmGrZlEu63F3DsguF8Fhd1WfDBRXqCYAWp/frvoPmjjWhAt/P3KD4SyKgTTtP178c2tmvmJC80XkxIAPeOTvdYV8CDZh91hItPuor2sql3XVc+tE9spMKv+lCN4InJR+8egUzmfiYHgFxD4PHRIzlsQUkbTvu+93ST0="
    #     }
    #   }
    # },
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", help="echo the string you use here",
                        default="gosync3.json")
    args = parser.parse_args()
    main(args)
