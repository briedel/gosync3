#!/usr/bin/env python
from __future__ import print_function
import argparse
import json
from globus_db_v2 import globus_db
import collections
import unicodedata

from util import parse_json_config


def append_unix_group(globus_groups, connect_groups):
    grps = [(group, gid["gid"]) for group, gid in connect_groups.iteritems()]
    grps_nms = zip(*grps)[0]
    gids = zip(*grps)[1]
    new_groups = [ggroup["name"] for ggroup in globus_groups
                  if ggroup["name"] not in grps_nms]
    max_gid = max(gids)
    for ngroup in new_groups:
        gid = max_gid + 1 if max_gid > 100000 else 100000
        grps.append((ngroup, gid))
        max_gid = max_gid + 1 if max_gid > 100000 else 100000
    new_grps = {group[0]: {"gid": group[1]} for group in grps}
    return new_grps


def find_alter_duplicate_gids(connect_groups):
    grps = [(group, gid["gid"]) for group, gid in connect_groups.iteritems()]
    grps_nms = zip(*grps)[0]
    gids = list(zip(*grps)[1])
    duplicate_gids = [item for item, count in collections.Counter(gids).items()
                      if count > 1]
    for dgid in duplicate_gids:
        indices = [i for i, x in enumerate(gids) if x == dgid]
        for iidx, idx in enumerate(indices):
            if iidx == 0:
                continue
            tgid = gids[idx] + 1
            while tgid in gids:
                tgid += 1
            gids[idx] = tgid
    alter_grps = {grp: {"gid": gids[idx]}
                  for idx, grp in enumerate(grps_nms, start=0)}
    return alter_grps


def decompose_sshkey(user):
    puppet_ssh_key = collections.defaultdict(dict)
    for key in user["ssh_pubkeys"]:
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
            puppet_ssh_key[user["email"]] = {
                "type": key_pieces[0],
                "key": key_pieces[1]}
    return puppet_ssh_key


def manage_user(globus_members, connect_users):
    new_members = [gmem for gmem in globus_members
                   if gmem["username"] not in connect_users.keys()]
    gusernames = [gmem["username"] for gmem in globus_members]
    deleted_members = [cmem for cmem in connect_users.keys()
                       if cmem not in gusernames]
    for gmem in globus_members:
        gmem["name"] = unicodedata.normalize(
            "NFKD", gmem["name"]).encode('ascii', 'ignore')
    uids = [userinfo["uid"]
            for username, userinfo in connect_users.iteritems()]
    max_uid = max(uids)
    for new_member in new_members:
        if "@" in new_member["username"]:
            print(new_member["username"])
            continue
        connect_users[new_member["username"]] = {
            "auth_refresh_token": None,
            "comment": new_member["name"],
            "email": new_member["email"],
            "gid": 1000,
            "manage_group": False,
            "nexus_refresh_token": None,
            "shell": "/bin/bash",
            "ssh_keys": decompose_sshkey(new_member),
            "uid": max_uid + 1 if max_uid >= 100000 else 100000,
            "groups": new_member["groups"]
        }
        max_uid = max_uid + 1 if max_uid >= 100000 else 100000
        if len(new_member["groups"]) == 1:
            print(new_member["username"])
    for gmem in globus_members:
        if gmem["username"] in new_members or "@" in gmem["username"]:
            continue
        json_ssh_key = decompose_sshkey(gmem)
        connect_users[gmem["username"]]["ssh_keys"] = json_ssh_key
        connect_users[gmem["username"]]["email"] = gmem["email"]
        connect_users[gmem["username"]]["groups"] = gmem["groups"]
    for dmem in deleted_members:
        connect_users.pop(dmem, None)
    return connect_users


def main(args):
    config = parse_json_config(args.config)
    globusdb = globus_db(config=config)
    globus_groups = globusdb.get_all_groups()
    globus_members = globusdb.get_all_users(get_user_groups=True)
    # member_groups = globusdb.get_user_groups()
    with open("test_groups.json", "r") as infile:
        user_groups_db = json.load(infile)
    user_groups_db["accounts::groups"] = find_alter_duplicate_gids(
        user_groups_db["accounts::groups"])
    user_groups_db["accounts::groups"] = append_unix_group(
        globus_groups, user_groups_db["accounts::groups"])
    user_groups_db["accounts::users"] = manage_user(
        globus_members, user_groups_db["accounts::users"])
    with open("test_groups_v2.json", "w") as outfile:
        json.dump(user_groups_db, outfile)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", help="echo the string you use here",
                        default="gosync3.json")
    args = parser.parse_args()
    main(args)
