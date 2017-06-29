#!/usr/bin/env python
from __future__ import print_function
import os
import logging as log
import json
import collections
import unicodedata
import subprocess
import datetime
import random

# TODOs:
## 1. Update the tokens, etc. 


class connect_db_json(object):
    def __init__(self, config=None):
        if config is None:
            log.fatal(("No config provided. "
                      "Please make sure to supply your own!"))
            raise RuntimeError()
        self.config = config
        with open(self.config["connect_db"]["db_file"], "r") as cdbf:
            self.db = json.load(cdbf)
        self.users = self.db["accounts::users"]
        self.uids = [user["uid"] for user in self.users.values()]
        self.groups = self.db["accounts::groups"]
        self.gids = [group["gid"] for group in self.groups.values()]

    def commit_old_version(self):
        """
        Commiting the old version of the connect json db to git
        """
        p = subprocess.Popen(
            ["git", "commit",
             self.config["connect_db"]["db_file"],
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

    def write_db(self, commit_old_version=False):
        """
        Write out json files. One with all the group and user information and
        another will all the user's emails.

        Args:
            commit_old_version (bool): Optional argument that allows you to
                                       make commit changes to the database
                                       to the codes github repo
        """
        if commit_old_version:
            self.commit_old_version()
        self.users = collections.OrderedDict(sorted(self.users.items()))
        self.groups = collections.OrderedDict(sorted(self.groups.items()))
        self.db = {"accounts::users": self.users,
                   "accounts::groups": self.groups}

        with open(self.config["connect_db"]["db_file"], "w") as cdbf:
            json.dump(self.db, cdbf, indent=4)

        if "email_file" in self.config["connect_db"].keys():
            if not os.path.exists("emails"):
                os.mkdir("emails")
            email_file = self.config["connect_db"]["email_file"]
            with open(os.path.join("emails", email_file), "w") as emf:
                emails = self.get_emails()
                json.dump(emails, emf, indent=4)
            for tg in self.config["globus"]["groups"]["top_level_groups"]:
                file_path = os.path.join("emails",
                                         ("_").join([tg, email_file]))
                with open(file_path, "w") as emf:
                    emails = self.get_emails(group=tg)
                    json.dump(emails, emf, indent=4)
        if "mailchimp_file" in self.config["connect_db"].keys():
            if not os.path.exists("mailchimp"):
                os.mkdir("mailchimp")
            mailchimp_file = self.config["connect_db"]["email_file"]
            with open(os.path.join("mailchimp", mailchimp_file), "w") as mcf:
                mailchimp_info = self.get_mailchimp_info()
                json.dump(mailchimp_info, mcf, indent=4)
            for tg in self.config["globus"]["groups"]["top_level_groups"]:
                file_path = os.path.join("mailchimp",
                                         ("_").join([tg,
                                                     mailchimp_file]))
                with open(file_path, "w") as mcf:
                    emails = self.get_mailchimp_info(group=tg)
                    json.dump(mailchimp_info, mcf, indent=4)

    def new_unix_id(self, ids, id_minium=100000):
        """

        Args:
            ids (list of ints): List of already used ids

        Returns:
            new_id (int): New ID for group or user
        """
        max_id = max(ids)
        new_id = (max_id + 1) if max_id >= id_minium else id_minium
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
            try:
                key_pieces = key.split(" ")
                if len(key_pieces) == 1:
                    # No spaces in a key. Usually means the key doesn't
                    # have the right format. Skipping the key in that case
                    log.warn("Malformed key: %s.", key)
                    log.warn("Malformed key by user: %s. Skipping key.", user["username"])
                    continue
                log.debug("SSH key pieces: %s", key_pieces)
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
            except:
                log.warn("Malformed key: %s.", key)
                log.warn("Malformed key by user: %s. Skipping key.", user["username"])
                continue
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
            # group's UNIX ID
            "gid": new_gid,
            # Number of active members
            "num_members": group["active_count"],
            # Globus group UUID
            "globus_uuid": group["id"]
        }
        self.gids.append(new_gid)

    def get_default_project(self, user):
        """
        Trying to guess the default project for a new user

        Args:
            user (dict): user information from Globus, pre-formatted
        """
        sub_groups = [g for g in user["groups"] if "." in g]
        top_groups = [g for g in user["groups"]
                      if ("." not in g and
                          g != self.config["globus"]["groups"]["root_group"])]
        if not top_groups:
            log.fatal(("User %s is only in the connect group."
                       "Please double check"), user["username"])
            raise RuntimeError()
        while len(sub_groups) > 1:
            # If there are more than one sub project we need to filter
            # out any of the default ones. First we remove the
            # "osg.ConnectTrain". If there are still more than
            # one projects, we filter out any project associated
            # with a user school and any OSG project,
            # if the user is a member of the other
            # connect instances, i.e. SPT, ATLAS, CMS, Duke
            if "osg.ConnectTrain" in sub_groups:
                sub_groups.remove("osg.ConnectTrain")
                break
            tmp_subgroups = []
            for sg in sub_groups:
                if ("UserSchool" in sg or
                    "SWC" in sg or
                    "wg" in sg or
                    "old" in sg or
                    any(g in sg.split(".")[-1] for g in top_groups)):
                    continue
                if len(top_groups) > 1 and "osg" in sg:
                    continue
                tmp_subgroups.append(sg)
            sub_groups = tmp_subgroups
        if len(sub_groups) > 0:
            return sub_groups[0]
        else:
            return top_groups[0]

    def add_user(self, user):
        """
        Adding users to json database

        Args:
            user (dict): user information from Globus, pre-formatted
        """
        new_uid = self.new_unix_id(self.uids)
        ssh_key = self.decompose_sshkey(user)
        self.users[user["username"]] = {
            # user's Globus Auth refresh token
            "auth_refresh_token": None,
            # user's full name in Globus
            "comment": self.remove_unicode(user["name"]),
            # user's email
            "email": user["email"],
            # default gid
            "gid": self.config["users"]["default_group"],
            # puppet/hiera config parameter
            "manage_group": False,
            # user's Globus Nexus refresh token
            "nexus_refresh_token": None,
            # default user shell
            "shell": "/bin/bash",
            # user's SSH key(s) from decompose_sshkey
            "ssh_keys": ssh_key,
            # user's UNIX id
            "uid": new_uid,
            # user's groups
            "groups": user["groups"],
            # Adding initial connect project
            "connect_project": self.get_default_project(user),
            # Pick a condor queue, 1 through 5, at random
            "condor_schedd": random.randint(1, 5)
        }
        self.uids.append(new_uid)

    def set_user_nologin(self, user):
        """
        Setting a user's shell to nologin. Used to "remove" a user

        Args:
            user (dict): user information from Globus, pre-formatted
        """
        self.users[user["username"]]["shell"] = "/sbin/nologin"

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
        self.groups[group["name"]]["num_members"] = group["active_count"]

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

    def get_auth_token(self, username):
        """
        Get Globus Auth token for a user

        Args:
            username (string): Globus username
        Returns:
            Globus Auth refresh token as a string
        """
        if username not in self.users:
            return None
        return self.users[username]["auth_refresh_token"]

    def get_nexus_token(self, username):
        """
        Get Globus Auth Nexus token for a user

        Args:
            username (string): Globus username
        Returns:
            Globus Nexus refresh token as a string
        """
        if username not in self.users:
            return None
        return self.users[username]["nexus_refresh_token"]

    def get_globus_tokens(self, username):
        """
        Get both Globus Auth and Nexues token for a user

        Args:
            username (string): Globus username
        Returns:
            Tuple of strings: Globus Auth and Nexus refresh tokens
        """
        return self.get_auth_token(username), self.get_nexus_token(username)

    def get_mailchimp_info(self, group=None):
        """
        Get the information for mailchimp: email, first and last name

        Args:
            group (string): Optional group whose user information
        Returns:
            Dict mapping username to email address and first and last name
        """
        if group is None:
            return {usr:
                    {"email": info["email"],
                     "first_name": info["comment"].split(" ")[0],
                     "last_name": info["comment"].split(" ")[-1]}
                    for usr, info in self.users.items()}
        else:
            return {usr:
                    {"email": info["email"],
                     "first_name": info["comment"].split(" ")[0],
                     "last_name": info["comment"].split(" ")[-1]}
                    for usr, info in self.users.items()
                    if group in info["groups"]}

    def get_emails(self, group=None):
        """
        Get the emails of a set of users. In this case either all users or
        optionally of a specified group

        Args:
            group (string): Optional group whose user emails you want
        Returns:
            Dict mapping username to email address
        """
        if group is None:
            return {usr: info["email"] for usr, info in self.users.items()}
        else:
            return {usr: info["email"] for usr, info in self.users.items()
                    if group in info["groups"]}

    def get_email(self, username):
        """
        Get email for a specified user

        Args:
            username (string):
        Returns:
            String with user's email address
        """
        return self.users[username]["email"]

    def update_auth_token(self, username, token):
        raise NotImplementedError()

    def update_nexus_token(self, username, token):
        raise NotImplementedError()
