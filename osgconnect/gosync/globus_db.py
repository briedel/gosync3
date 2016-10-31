from __future__ import print_function
import logging as log
import time
import socket
from collections import defaultdict

from util import uniclean

try:
    from nexus import GlobusOnlineRestClient
except:
    """
    Trying to see if we can import the Globus Auth framework
    WARNING!!!! Not yet supported. Mostly cause Globus Auth
    has no group support
    TODO: Support Globus Auth
    """
    log.error(("Cannot import Globus Nexus. Trying to "
               "import Globus SDK Auth Client"))
    try:
        from globus_sdk import AuthClient
    except:
        log.error(("Cannot import Globus Auth Client "
                   "or Globus Nexus. Exiting"))
        raise RuntimeError()


class globus_db(object):
    def __init__(self, config=None):
        if config is None:
            log.warn(("No config provided. "
                      "Please make sure to supply your own!"))
        self.config = config

    def get_globus_client(self, config=None):
        raise NotImplementedError()

    def get_globus_groups(self, roles=None, client=None):
        raise NotImplementedError()

    def filter_group(self, groups=None, group_names=None, filter_func=None):
        raise NotImplementedError()

    def strip_replace_prefix(group, prefixes):
        raise NotImplementedError()

    def get_groups(self,
                   filters_prefix=None,
                   filters_name=None,
                   config=None,
                   all_groups=None,
                   dump_root_group=True,
                   remove_unicode=False):
        raise NotImplementedError()

    def get_groupid(self, groups=None, names=None):
        raise NotImplementedError()

    def get_globus_group_members(self, config=None,
                                 client=None, globus_groups=None,
                                 group_names=None, only_top_level=False):
        raise NotImplementedError()


class globus_db_nexus(globus_db):
    """
    A class to hide some of the goriness of the globus
    """
    def __init__(self, config=None):
        if config is None:
            log.warn(("No config provided. "
                      "Please make sure to supply your own!"))
        self.config = config
        self.client = self.get_globus_client()
        self.all_groups = None
        # self.all_groups = self.get_globus_groups(
        #     self.config['globus']['roles'])
        self.groups = self.get_groups()
        (self.group_members,
         self.member_group) = self.get_globus_group_members()

    def get_globus_client(self, config=None):
        """
        Get Globus Nexus RESTful client

        Returns:
            client: Globus Nexus RESTful client
        """
        if config is None:
            config = self.config
        nexus_config = {"server": config['globus']['server'],
                        "client": config['globus']['client_user'],
                        "client_secret": config['secrets']['connect']}
        client = GlobusOnlineRestClient(config=nexus_config)
        return client

    def get_globus_groups(self, roles=None, client=None):
        """
        Get list of Globus groups

        Args:
            roles: Globus Nexus roles

        Returns:
            all_groups: List of all groups in Globus Nexus groups
                         that are associated with a role
        """
        if client is None:
            client = self.client
        if roles is None:
            roles = self.config['globus']['roles']
        if isinstance(roles, str):
            all_groups = client.get_group_list(my_roles=[roles])[1]
        if isinstance(roles, list):
            all_groups = client.get_group_list(my_roles=roles)[1]
        return all_groups

    def filter_group(self, groups=None, group_names=None, filter_func=None):
        """
        Return group(s) we are interested in

        :param groups: List of Globus Nexus groups
        :param group_names: Group(s) we are interested in
        :return: List of or individual group(s)
        """
        if groups is None:
            groups = self.groups
        if group_names is not None:
            if isinstance(group_names, str):
                group_names = [group_names]
            filtered_groups = [g for g in groups
                               if g['name'] in group_names]
            if isinstance(group_names, list):
                return filtered_groups
            elif isinstance(group_names, str):
                return filtered_groups[0]
        elif filter_func is not None:
            return filter_func()

    def strip_replace_prefix(group, prefixes):
        """
        Stripping Globus specific prefixes from
        Globus group names

        :param group: Group to filtered
        :param filters: Filter
        :return: Group without filter
        """
        if not (isinstance(prefixes, list) or
                isinstance(prefixes, tuple)):
            prefixes = tuple(prefixes)
        for p in prefixes:
            if "osg" in p:
                return group.split('.')[-1]
            elif ("duke" in p or "atlas" in p):
                return group.replace('.', '-')

    def get_groups(self,
                   filters_prefix=None,
                   filters_name=None,
                   config=None,
                   all_groups=None,
                   dump_root_group=True,
                   remove_unicode=False):
        """
        fjgas

        Args:
            filters_prefix: Tuple of keywords that will filter the groups by
            filters_name:
            config:
            all_groups:
            dump_root_group: Bool whether to include the top-level
                             group, i.e. "connect"
            remove_unicode: Bool whether to remove the unicode
                            characters from the group paramaters

        Returns:
            groups: List of all groups that start with one of the filters
                    and optionally the root group
        """
        if remove_unicode and all_groups is not None:
            all_groups = uniclean(all_groups)
        elif remove_unicode:
            all_groups = uniclean(self.all_groups)
        elif all_groups is None:
            all_groups = self.all_groups
        if all_groups is None:
            self.all_groups = self.get_globus_groups()
            all_groups = self.all_groups
        if filters_prefix is None:
            filters_prefix = tuple(self.config["groups"]["filter_prefix"])
        elif not isinstance(filters_prefix, tuple):
            filters_prefix = tuple(filters_prefix)
        if not isinstance(filters_name, tuple):
            filters_name = tuple(filters_name)
        root_group = self.config["globus"]["root_group"]
        if filters_name is None:

            def filter_group(g):
                result = ((g['name'].startswith(filters_prefix) or
                          (g['name'] == root_group and
                           dump_root_group)))
                return result
        else:
            if not isinstance(filters_name, tuple):
                filters_name = tuple(filters_name)

            def filter_group(g):
                result = ((g['name'].startswith(filters_prefix) or
                          (g['name'] == root_group and
                           dump_root_group)) and
                          (g['name'] in filters_name))
                return result
        self.groups = [g for g in all_groups if filter_group(g)]
        self.groups.sort(key=lambda k: k['name'])
        return self.groups

    def get_groupid(self, groups=None, names=None):
        """
        Get the Globus Nexus ID for the group

        :param groups: List of Globus Nexus groups
        :param names: Group(s) we are interested in
        :return: List of or individual group(s) ids
        """
        if groups is None:
            groups = self.groups
        if names is not None:
            groups = self.filter_groups(names, groups=groups)
        if isinstance(groups, list):
            ids = {g['id']: g for g in groups}
            return ids
        else:
            return {groups['id']: groups}

    def get_globus_group_members(self, config=None,
                                 client=None, globus_groups=None,
                                 group_names=None, only_top_level=False):
        """
        Getting all the active members of the group from globus nexus

        Args:
            config: Configuration parameters dict()
            client: Globus Nexus RESTful client
            globus_groups:
            groups:

        Returns:
            
        """
        # Dict of group to members
        self.group_members = defaultdict(dict)
        # Dict of members to group
        self.member_group = defaultdict(dict)
        if client is None:
            client = self.client
        if config is None:
            config = self.config
        # Making sure we get the right groups
        if globus_groups is None and group_names is None:
            group_ids = self.get_groupid()
        elif globus_groups is None and group_names is not None:
            if not (isinstance(group_names, list) or
                    isinstance(group_names, tuple)):
                group_names = tuple(group_names)
            group_ids = self.get_groupid(names=group_names)
        elif globus_groups is None and only_top_level:
            group_ids = self.get_groupid(names=config["globus"]["root_group"])
        elif globus_groups is not None and group_names is not None:
            group_ids = self.get_groupid(groups=globus_groups,
                                         names=group_names)
        elif globus_groups is not None and group_names is None:
            group_ids = self.get_groupid(groups=globus_groups)
        elif globus_groups is not None and only_top_level:
            group_ids = self.get_groupid(globus_groups,
                                         config["globus"]["root_group"])
        # Loop though selected groups
        for group_id, group in group_ids.items():
            # Getting members
            try:
                headers, response = client.get_group_members(group_id)
            except socket.timeout:
                logging.error(("Globus Nexus Server "
                               "response timed out. Skipping."))
                time.sleep(5)
                continue
            # Loop through group members and build output
            for member in response['members']:
                if not member or member['status'] != 'active':
                    continue
                username = str(member['username'])
                user_info = client.get_user(username)
                if group_ids in self.roup_members:
                    self.group_members[group_ids]["members"].append(
                        user_info)
                else:
                    self.group_members[group_ids] = {
                        "members": [user_info],
                        "group": group}
                self.member_group[username] = {
                    "user_profile": user_info,
                    "group_id": group_id,
                    "group": group}
        return self.group_members, self.member_group
