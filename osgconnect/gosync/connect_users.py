from __future__ import print_function
import logging as log

from collections import defaultdict


class connect_users(object):
    def __init__(self, config, options):
        self.config = config
        self.options = options
        self.users = defaultdict(dict)
        self.get_connect_userinfo()
        self.usernames = list(self.users.keys())
        self.get_connect_user_ids()

    def get_connect_userinfo(self, config=None, re_intialize=False):
        """
        Parse passwd file to see what users were already provisioned

        Args:
            config: Configuration parameters dict()
            options: Command line options

        Return:
            user_info: Tuple if lists, where every list is the user information
                       as stored in a /etc/password file
        """
        if config is None:
            config = self.config
        if (len(self.users.keys()) == 0 or
           re_intialize):
            with open(config["users"]["passwd_file"], "rt") as f:
                for line in f:
                    passwd_line = line.rstrip("\n").split(":")
                    self.users[passwd_line[0]] = {
                        "auth": passwd_line[1],
                        "user_id":  passwd_line[2],
                        "group_id": passwd_line[3],
                        "comment": passwd_line[4],
                        "home_dir": passwd_line[5],
                        "shell": passwd_line[6]}
            return self.users
        else:
            return self.users

    def get_connect_usernames(self, config=None):
        """
        Get tuple of already provisioned usernames. Works either by
        getting the output of get_connect_userinfo() or by getting
        the configuration and options to call get_connect_userinfo()
        internally.

        :param config: (optional requires options) Configuration parameters dict()
        :param options: (optional requires config) Command line options
        :param users: (optional) list of user information
        :return: Tuple of already provisioned usernames
        """
        self.usernames = list(self.users.keys())
        return self.usernames


    def get_connect_user_ids(self, config=None, options=None, users=None):
        """
        Get tuple of already used user ids. Works either by
        getting the output of get_connect_userinfo() or by getting
        the configuration and options to call get_connect_userinfo()
        internally.

        :param config: (optional requires options) Configuration parameters dict()
        :param options: (optional requires config) Command line options
        :param users: (optional) list of user information
        :return: Tuple of already used user ids
        """
        self.user_ids = [v["user_id"] 
                                 for k, v in self.users.iteritems()]
        return self.user_ids
