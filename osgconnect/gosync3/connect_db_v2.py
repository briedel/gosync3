#!/usr/bin/env python
from __future__ import print_function
import logging as log
import json
import collections
import unicodedata
import subprocess
import datetime


class connect_db(object):
    def __init__(self, config):
        self.config = config
        with open(self.config["connectdb"]["db_file"], "r") as cdbf:
            self.db = json.load(cdbf)
        self.users = self.db["accounts::users"]
        self.uids = [user["uid"] for user in self.users.values()]
        self.groups = self.db["accounts::groups"]
        self.gids = [group["uid"] for group in self.groups.values()]

    def commit_old_version(self):
        """
        Commiting the old version of the connect json db to git
        """
        p = subprocess.Popen(
            ["git", "commit",
             self.config["connectdb"]["db_file"],
             "-m", "Committing backup version %s" % datetime.datetime.now()],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        git_out = p.communicate()
        log.info("std out git commit = %s", git_out[0])
        log.info("std err git commit = %s", git_out[1])
        p = subprocess.Popen(
            ["git", "push"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        git_out = p.communicate()
        log.info("std out git commit = %s", git_out[0])
        log.info("std err git commit = %s", git_out[1])


    def write_db(self):
        """
        Write out json file
        """
        self.commit_old_version()
        self.db = {"accounts::users": self.users,
                   "accounts::groups": self.groups}
        with open(self.config["connectdb"]["db_file"], "w") as cdbf:
            json.dump(self.db, cdbf)

    def new_unix_id(self, ids):
        """

        Args:
            ids (list of ints): List of already used ids

        Returns:
            new_id (int): New ID for group or user
        """
        max_id = max(ids)
        new_id = (max(max_id) + 1) if max_id > 100000 else 100000
        return new_id

    def decompose_sshkey(self, user):
        """
        Break up SSH key into format needed by hiera/puppet for user 
        generation

        Args:
            user (dict): User information with ssh keys

        Returns:
            puppet_ssh_key (dict): SSH key formatted for hiera/puppet
        """
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

    # def find_alter_duplicate_gids(self):
    #     ### Get this working again
    #     duplicate_gids = [item for item, count in
    #                       collections.Counter(self.gids).items() if count > 1]
    #     for dgid in duplicate_gids:
    #         indices = [i for i, x in enumerate(gids) if x == dgid]
    #         for iidx, idx in enumerate(indices):
    #             if iidx == 0:
    #                 continue
    #             tgid = gids[idx] + 1
    #             while tgid in gids:
    #                 tgid += 1
    #             gids[idx] = tgid
    #     alter_grps = {grp: {"gid": self.gids[idx], "mem_count": gr}
    #                   for idx, grp in enumerate(grps_nms, start=0)}
    #     return alter_grps

    def remove_unicode(self, unicode_string):
        """
        Remove any unicode from a string

        Args:
            unicode_string (string): Unicode formated string

        Returns:
            Ascii formartted string
        """
        return unicodedata.normalize("NFKD", unicode_string).encode('ascii',
                                                                    'ignore')

    def add_group(self, group):
        """
        Adding a group to the json database

        Args:
            group (dict): Group information from Globus    
        """
        new_gid = self.new_unix_id(self.gids)
        self.groups[group["name"]] = {
            "gid": new_gid,
            "num_users": group["active_count"]
        }
        self.gids.append(new_gid)

    def add_user(self, user):
        """
        Adding users to json database

        Args:
            user (dict): user information from Globus, pre-formatted
        """
        new_uid = self.new_unix_id(self.uids)
        ssh_key = self.decompose_sshkey(user)
        self.users[user["username"]] = {
            "auth_refresh_token": None,
            "comment": self.remove_unicode(user["name"]),
            "email": user["email"],
            "gid": 1000,
            "manage_group": False,
            "nexus_refresh_token": None,
            "shell": "/bin/bash",
            "ssh_keys": ssh_key,
            "uid": new_uid,
            "groups": user["groups"]
        }
        self.uids.append(new_uid)

    def update_user(self, user):
        """
        Updating user information, i.e. email, SSH key, group membership

        Args:
            user (dict): user information from Globus, pre-formatted
        """
        ssh_key = self.decompose_sshkey(user)
        self.users[user["username"]]["email"] = user["email"]
        self.users[user["username"]]["ssh_keys"] = ssh_key
        self.users[user["username"]]["groups"] = user["groups"]

    def update_group(self, group):
        """
        Update group information, i.e. number of members

        Args:
            group (dict): Group information from Globus  
        """
        self.groups[group["name"]] = {
            "gid": self.groups[group["name"]]["gid"],
            "num_members": group["active_count"]
        }

    def get_user(self, username):
        """
        Return user information

        Args:
            username (string): Username to retrieve
        Returns:
            user information dict
        """
        return self.users[username]

    def get_group(self, group_name):
        """
        Return group information

        Args:
            group_name (string): name of group to be retrieved
        Returns:
            group information dict
        """
        return self.groups[group_name]

    def get_member_count(self, group_name):
        """
        Get membership count stored in json database

        Args:
            group_name (string): name group to be retrieved
        Returns
            Number of group members (ints)
        """
        group = self.get_group(group_name)
        return group["num_members"]
