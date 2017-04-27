from __future__ import print_function
import logging as log
import sys
import time
import socket
import re
from collections import defaultdict
from connect_db import connect_db

from util import uniclean, retry

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
    raise RuntimeError()
try:
    from globus_sdk import AuthClient
except:
    log.error(("Cannot import Globus Auth Client "
               "or Globus Nexus. Exiting"))
    raise RuntimeError()


class globus_db(object):
    """
    Virutal class to implement an interface to the Globus user
    database
    """
    def __init__(self, config=None):
        """
        Intiliazer
        Args:
            config: Configuration dict()
        """
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

    def get_group_members(self, config=None,
                          client=None, globus_groups=None,
                          group_names=None, only_top_level=False):
        raise NotImplementedError()


class globus_db_nexus(globus_db):
    """
    A class to hide some of the goriness of the globus
    """
    def __init__(self, config=None, get_members=False):
        """
        Intiliazer
        Args:
            config: Configuration dict()
            get_members: Get the members of the groups
        """
        if config is None:
            log.warn(("No config provided. "
                      "Please make sure to supply your own!"))
        self.config = config
        self.get_globus_client()
        self.all_groups = None
        # self.all_groups = self.get_globus_groups(
        #     self.config['globus']['nexus_roles'])
        self.get_groups()
        if get_members:
            self.get_globus_group_members()

    def get_globus_client(self, config=None):
        """
        Get Globus Nexus RESTful client

        Args:
            config: Configuration dict()

        Returns:
            client: Globus Nexus RESTful client
        """
        if config is None:
            config = self.config
        nexus_config = {"server": config['globus']['server'],
                        "client": config['globus']['client_user'],
                        "client_secret": config['secrets']['connect']}
        self.client = GlobusOnlineRestClient(config=nexus_config)
        log.debug("Got Globus Nexus client")
        return self.client

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
            roles = self.config['globus']['nexus_roles']
        if isinstance(roles, str):
            self.all_groups = client.get_group_list(my_roles=[roles])[1]
        if isinstance(roles, list):
            self.all_groups = client.get_group_list(my_roles=roles)[1]
        return self.all_groups

    def filter_groups(self, groups=None, group_names=None, filter_func=None):
        """
        Return group(s) we are interested in

        Args:
            groups: List of Globus Nexus groups
            group_names: Group(s) we are interested in

        Returns:
            filtered_groups: List or instance of the
                             group object of the Globus DB
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
            # still work in process
            # mostly playground to figure out
            # where you can pass a function
            # to filter instead
            raise NotImplementedError()
        else:
            log.fatal("Requires a set of group names to consider")
            raise RuntimeError()

    def strip_replace_prefix(group, prefixes):
        """
        Stripping Globus specific prefixes from
        Globus group names

        TODO: Make this configurable

        Args:
            group: Group name
            prefixes: Prefixes of group names

        Returns:
            Group name without the prefix
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
        Get the groups in the Globus DB

        Args:
            filters_prefix: Tuple of keywords that will filter the groups by
            filters_name: Tuple of names by which to filter the groups
            config: config dict()
            all_groups: Bool to all groups or not
            dump_root_group: Bool whether to include the top-level
                             group, i.e. "connect"
            remove_unicode: Bool whether to remove the unicode
                            characters from the group paramaters

        Returns:
            groups: List of all groups that start with one of the filters
                    and optionally the root group
        """
        log.debug("Getting groups")
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
        root_group = self.config["globus"]["root_group"]
        log.debug("Filtering groups")
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
        log.debug("Got groups")
        return self.groups

    def get_groupid(self, groups=None, names=None):
        """
        Get the Globus Nexus ID for the group

        Args:
            groups: List of Globus Nexus groups
            names: Group(s) we are interested in

        Returns:
            ids: Dict() mapping group(s) ids group
        """
        if groups is None:
            groups = self.groups
        if names is not None:
            groups = self.filter_groups(group_names=names, groups=groups)
        if isinstance(groups, list):
            ids = dict((g['id'], g) for g in groups)
            return ids
        else:
            return {groups['id']: groups}

    def get_group_members(self, config=None,
                                 client=None, globus_groups=None,
                                 group_names=None, get_user_profile=True,
                                 only_top_level=False, no_top_level=False):
        """
        Getting all the active members of the group from globus nexus

        Args:
            config: Configuration parameters dict()
            client: Globus Nexus RESTful client
            globus_groups:
            groups:

        Returns:
            
        """
        log.debug("Getting users")
        # Dict of group to members
        self.group_members = defaultdict(dict)
        # Dict of members to group
        self.member_group = defaultdict(dict)
        if client is None:
            client = self.client
        if config is None:
            config = self.config
        # Making sure we get the right groups
        if (globus_groups is None and
            group_names is None and
            not only_top_level):
            group_ids = self.get_groupid()
        elif globus_groups is None and group_names is not None:
            if not (isinstance(group_names, list) or
                    isinstance(group_names, tuple)):
                group_names = tuple(group_names)
            group_ids = self.get_groupid(names=group_names)
        elif globus_groups is None and only_top_level:
            log.debug("Getting only top level group")
            group_ids = self.get_groupid(names=config["globus"]["root_group"])
        elif globus_groups is not None and group_names is not None:
            group_ids = self.get_groupid(groups=globus_groups,
                                         names=group_names)
        elif globus_groups is not None and group_names is None:
            group_ids = self.get_groupid(groups=globus_groups)
        elif globus_groups is not None and only_top_level:
            group_ids = self.get_groupid(globus_groups,
                                         config["globus"]["root_group"])
        log.debug("Looping through groups")
        # Loop though selected groups
        for group_id, group in group_ids.iteritems():
            if (no_top_level and
               group["name"] == config["globus"]["root_group"]):
                continue
            # Getting members
            try:
                headers, response = client.get_group_members(group_id)
            except socket.timeout:
                log.error(("Globus Nexus Server "
                           "response timed out. Skipping."))
                time.sleep(5)
                continue
            log.debug("Looping through users for group %s",
                      group["name"])
            for member in response['members']:
                if not member or member['status'] != 'active':
                    continue
                username = str(member['username'])
                if get_user_profile:
                    try:
                        user_info = client.get_user(username)
                    except socket.timeout:
                        # if we time out, pause and resume, skipping current
                        log.error(("Socket timed out. Waiting for 5 seconds. "
                                   "User %s was skipped") % username)
                        time.sleep(5)
                        continue
                else:
                    user_info = member
                if group["name"] in self.group_members:
                    self.group_members[group["name"]]["members"].append(
                        user_info)
                    self.group_members[group["name"]]["usernames"].append(username)
                else:
                    self.group_members[group["name"]] = {
                        "members": [user_info],
                        "usernames": [username],
                        "group": group}
                if (group["name"] != config["globus"]["root_group"] or
                    only_top_level):
                    self.member_group[username] = {
                        "user_profile": user_info,
                        "group_id": group_id,
                        "group_name": group["name"],
                        "group": group,
                        "top_group": (group["name"].split(".")[0]
                                      if not "project" in group["name"]
                                      else "osg")}
        return self.group_members, self.member_group


class MyGlobusOnlineRestClient(GlobusOnlineRestClient):
    def __init__(self, nexus_config=None, nexus_config_file=None):
        GlobusOnlineRestClient.__init__(self, config=nexus_config, config_file=nexus_config_file)

    def get_group_membership(self, username, use_session_cookies=False):
        url = '/users/' + username + '/groups'
        return self._issue_rest_request(url)


class globus_db_hybrid(globus_db):
    """
    A class to hide some of the goriness of the globus
    """
    def __init__(self, config=None,
                 connect_db=None,
                 get_groups=False,
                 get_members=False,
                 only_new_members=False,
                 only_update_members=False,
                 consistency_check=False):
        """
        Intiliazer
        Args:
            config: Configuration dict()
            get_members: Get the members of the groups
        """
        if config is None:
            log.warn(("No config provided. "
                      "Please make sure to supply your own!"))
        self.config = config
        if not isinstance(self.config, dict):
            log.fatal("Config is not dict")
            raise RuntimeError()
        self.connect_db = connect_db
        # if not isinstance(self.connect_db, connect_db):
        #     log.fatal("No transaction handle with connect DB available")
        #     raise RuntimeError()
        self.get_globus_client()
        self.groups = None
        self.only_new_members = only_new_members
        self.only_update_members = only_update_members
        self.consistency_check = consistency_check
        # self.all_groups = self.get_globus_groups(
        #     self.config['globus']['nexus_roles'])
        if get_groups:
            self.get_groups()
        if get_members:
            self.get_group_members()
        self.users = None

    def get_globus_client(self, config=None):
        """
        Get Globus Nexus RESTful client

        Args:
            config: Configuration dict()

        Returns:
            client: Globus Nexus RESTful client
        """
        if config is None:
            config = self.config
        nexus_config = {"server": config['globus']['server'],
                        "client": config['globus']['client_user'],
                        "client_secret": config['globus']['secret']}
        self.client = MyGlobusOnlineRestClient(nexus_config=nexus_config)
        log.debug("Got Globus Nexus client")
        return self.client

    def get_user_groups(self, username):
        return self.client.get_group_membership(username)

    @retry(socket.timeout, tries=4, delay=5, backoff=2, logger=log)
    def get_globus_group(self, roles=None, client=None):
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
            roles = self.config['globus']['nexus_roles']
        if isinstance(roles, str):
            self.all_groups = client.get_group_list(my_roles=[roles])[1]
        if isinstance(roles, list):
            self.all_groups = client.get_group_list(my_roles=roles)[1]
        return self.all_groups

    @retry(socket.timeout, tries=4, delay=5, backoff=2, logger=log)
    def get_globus_group_tree(self, client=None,
                              root_group_uuid=None, depth=3):
        if client is None:
            client = self.client
        if root_group_uuid is None:
            root_group_uuid = self.config['globus']['root_group_uuid']
        header, self.group_tree = client.get_group_tree(root_group_uuid, depth)
        if (isinstance(self.group_tree, dict) and
           self.group_tree["name"] == self.config["globus"]["root_group"]):
            log.debug("Got Group Tree from Globus")
        return self.group_tree

    def filter_groups(self, groups=None, group_names=None, filter_func=None):
        """
        Return group(s) we are interested in

        Args:
            groups: List of Globus Nexus groups
            group_names: Group(s) we are interested in

        Returns:
            filtered_groups: List or instance of the
                             group object of the Globus DB
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
            # still work in process
            # mostly playground to figure out
            # where you can pass a function
            # to filter instead
            raise NotImplementedError()
        else:
            log.fatal("Requires a set of group names to consider")
            raise RuntimeError()

    def strip_replace_prefix(group, prefixes):
        """
        Stripping Globus specific prefixes from
        Globus group names

        TODO: Make this configurable

        Args:
            group: Group name
            prefixes: Prefixes of group names

        Returns:
            Group name without the prefix
        """
        if not (isinstance(prefixes, list) or
                isinstance(prefixes, tuple)):
            prefixes = tuple(prefixes)
        for p in prefixes:
            if "osg" in p:
                return group.split('.')[-1]
            elif ("duke" in p or "atlas" in p):
                return group.replace('.', '-')

    @retry(socket.timeout, tries=4, delay=5, backoff=2, logger=log)
    def get_group_summary(self, group, client=None):
        if client is None:
            client = self.client
        if "id" not in group:
            log.fatal("No Group UUID available for group %s ",
                      group["name"])
            raise RuntimeError()
        header, group_summary = client.get_group_summary(group["id"])
        return group_summary

    def get_groups_summary(self, client=None, groups=None):
        if client is None:
            client = self.client
        if groups is None:
            all_group_summary = [self.get_group_summary(g)
                                 for g in self.groups]
            return all_group_summary
        else:
            if not isinstance(groups, list):
                groups = [groups]
            group_summary = [self.get_group_summary(g)
                             for group in groups]
            return group_summary

    def combine_group_info(self, group, group_summary):
        group_info = {}
        group_info["id"] = group["id"]
        group_info["num_members"] = group_summary["active_count"]
        # if self.consistency_check:
        #     self.convert_group_desc(group_info, group, group_summary)
        return group_info

    # def remove_html(self, text):
    #     dehtml = re.compile('<[^>]+>')
    #     new_text = dehtml.sub('',
    #                           text.encode('utf-8',
    #                                       'ignore'))
    #     return new_text

    # def convert_go_group_desc(self, desc):
    #     textdesc = self.remove_html(desc)
    #     group_desc = defaultdict(str)
    #     for section in textdesc.split("\n"):
    #         split = section.split(":")
    #         # print(split)
    #         if len(split) < 2:
    #             continue
    #         elif len(split) > 2:
    #             log.fatal("WTF")
    #         group_desc[split[0]] = split[1].strip()
    #     return group_desc

    # def convert_group_desc(self, group_info, group, group_summary):
    #     description = self.convert_go_group_desc(
    #         group_summary["description"])
    #     if not group["hasChildren"]:
    #         group_info["short_name"] = description["Project Short Name"]
    #         group_info["discipline"] = description["Field of Science"]
    #         try:
    #             group_info["other_discipline"] = description[
    #                 "Field of Science (if Other)"]
    #         except:
    #             raise RuntimeWarning("Not other discipline")
    #         group_info["pi"] = description["PI Name"]
    #         group_info["pi_email"] = description["PI Email"]
    #         group_info["pi_org"] = description["Organization"]
    #         group_info["pi_dept"] = description["Department"]
    #         group_info["join_date"] = description["Join Date"]
    #         group_info["contact_name"] = description["Field of Science"]
    #         group_info["contact_email"] = description["Field of Science"]
    #         group_info["phone"] = description["Field of Science"]
    #         group_info["description"] = description["Project Description"]
    #     else:
    #         group_info["description"] = self.remove_html(
    #             group_summary["description"])

    def get_group_info(self, group):
        summary = self.get_group_summary(group)
        group_info = self.combine_group_info(group,
                                             summary)
        return group_info

    def get_groups(self,
                   client=None,
                   filters_top_group=None,
                   filters_names=None,
                   update=True):
        """
        Get the groups in the Globus DB

        Args:
            filters_prefix: Tuple of keywords that will filter the groups by
            filters_name: Tuple of names by which to filter the groups
            config: config dict()
            all_groups: Bool to all groups or not
            dump_root_group: Bool whether to include the top-level
                             group, i.e. "connect"
            remove_unicode: Bool whether to remove the unicode
                            characters from the group paramaters

        Returns:
            groups: List of all groups that start with one of the filters
                    and optionally the root group
        """
        if client is None:
            client = self.client
        if self.groups is not None and not update:
            return self.groups
        if (filters_top_group is not None and
           not isinstance(filters_top_group, list)):
            filters_top_group = [filters_top_group]
        if (filters_names is not None and
           not isinstance(filters_names, list)):
            filters_names = [filters_names]
        log.debug("Getting group information and assembling tree")
        self.get_globus_group_tree()
        group_info_tree = defaultdict(dict)
        group_info_tree[
            self.group_tree["name"]] = self.get_group_info(self.group_tree)
        # If we are only updating the members, we need to just get all the
        # members in the connect group
        if self.only_update_members:
            self.groups = group_info_tree
            return self.groups
        # If we are only looking for new members and the group count has not
        # changed then, we will just exit
        if self.check_new_members("connect",
                                  group_info_tree["connect"]["num_members"]):
            log.info("Nothing to do. Bye!")
            sys.exit()
        for top_child in self.group_tree["children"]:
            if self.process_child(group_info_tree, top_child,
                                  self.group_tree["name"],
                                  filters_group=filters_top_group):
                continue
            if (not top_child["hasChildren"] or
               "children" not in top_child.keys()):
                continue
            for child in top_child["children"]:
                if self.process_child(group_info_tree, child,
                                      top_child["name"],
                                      filters_group=filters_names):
                    continue
        self.groups = group_info_tree
        return self.groups

    def process_child(self, group_info_tree, child, top_group,
                      filters_group=None):
        if self.check_filters(child["name"], filters_group):
            return True
        group_info = self.get_group_info(child)
        if self.check_new_members(child["name"],
                                  group_info["num_members"]):
            return True
        if top_group == self.config["globus"]["root_group"]:
            group_info_tree[self.group_tree["name"]][child["name"]] = {
                "info": group_info}
        else:
            group_info_tree[self.group_tree["name"]][top_group][
                child["name"]] = group_info
        return False

    def check_new_members(self, group_name, group_count):
        return (self.only_new_members and
                self.check_group_membership_changes(group_name, group_count))

    def check_filters(self, term, filters):
        return (filters is not None and term not in filters)

    def check_group_membership_changes(self, group_name, globus_member_count):
        connect_member_count = self.connect_db.get_member_count(group_name)
        return (connect_member_count == globus_member_count)

    def get_group_members(self, group_name=None, repopulate=False, pretty_users=False):
        log.debug("Getting Group Users")
        users = {}
        if self.groups is None:
            self.get_groups(filters_names=group_name)
        if self.users is not None and repopulate:
            return self.users
        root_group = self.config["globus"]["root_group"]
        if ((group_name is None and self.only_update_members) or
           group_name == root_group):
            group_id = self.groups[root_group]["id"]
            members = self.wrapped_get_group_members(group_id)
            users["connect"] = members["members"]
        else:
            for top_child in self.groups[root_group].keys():
                if group_name is not None:
                    if "." in group_name:
                        top_child_limit = group_name.split(".")[0]
                    else:
                        top_child_limit = group_name
                if (group_name is not None and
                   top_child != top_child_limit):
                    continue
                if top_child == "num_members" or top_child == "id":
                    continue
                group_id = self.groups[root_group][top_child]["info"]["id"]
                members = self.wrapped_get_group_members(group_id)
                if top_child == "info" or top_child == "num_members":
                    continue
                users[top_child] = members["members"]
                for child in self.groups[root_group][top_child].keys():
                    if (group_name is not None and
                        group_name not in self.groups[
                            root_group][top_child].keys()):
                        continue
                    if child == "info" or child == "num_members":
                        continue
                    group_id = self.groups[root_group][top_child][child]["id"]
                    members = self.wrapped_get_group_members(group_id)
                    users[child] = members["members"]
        self.users = {group: [self.get_globus_member_info(user,
                                  pretty_profile=pretty_users)
                              for user in users
                              if (user["status"] == "active")]
                              # if (user["status"] != "rejected" and
                              #     user["status"] != "invited")]
                      for group, users in users.iteritems()}
        return self.users

    @retry(socket.timeout, tries=4, delay=5, backoff=2, logger=log)
    def get_globus_member_info(self, member, pretty_profile=False):
        headers, member_profile = self.client.get_user(member["username"])
        if pretty_profile:
            member_profile = self.prettify_user_profile(member_profile)
        return member_profile

    def prettify_user_profile(self, member_profile):
        new_member_profile = {}
        required_keys = ["username", "ssh_pubkeys", "custom_fields",
                         "fullname", "email"]
        for k, v in member_profile.iteritems():
            if v == "briedel":
                print(member_profile)
            if k not in required_keys:
                continue
            if k != "custom_fields":
                if k == "ssh_pubkeys":
                    for key in v:
                        if k not in new_member_profile.keys():
                            new_member_profile[k] = []
                        new_member_profile[k].append(key['ssh_key'])
                    if not v:
                        new_member_profile[k] = []
                else:
                    new_member_profile[k] = v
            else:
                for sk, sv in v.iteritems():
                    if sk in new_member_profile.keys():
                        continue
                    new_member_profile[sk] = sv
        return new_member_profile

    def push_new_group_globus_db(self):
        if not isinstance(self.connect_db, connect_db):
            log.fatal("No transaction handle with connect DB available")
            raise RuntimeError()

    @retry(socket.timeout, tries=4, delay=5, backoff=2, logger=log)
    def wrapped_get_group_members(self, group_id):
        headers, response = self.client.get_group_members(group_id)
        return response

    # def get_globus_group_members(self, config=None,
    #                              client=None, globus_groups=None,
    #                              group_names=None, get_user_profile=True,
    #                              only_top_level=False, no_top_level=False):
    #     """
    #     Getting all the active members of the group from globus nexus

    #     Args:
    #         config: Configuration parameters dict()
    #         client: Globus Nexus RESTful client
    #         globus_groups:
    #         groups:

    #     Returns:
            
    #     """
    #     log.debug("Getting users")
    #     # Dict of group to members
    #     self.group_members = defaultdict(dict)
    #     # Dict of members to group
    #     self.member_group = defaultdict(dict)
    #     if client is None:
    #         client = self.client
    #     if config is None:
    #         config = self.config
    #     # Making sure we get the right groups
    #     if (globus_groups is None and
    #         group_names is None and
    #         not only_top_level):
    #         group_ids = self.get_groupid()
    #     elif globus_groups is None and group_names is not None:
    #         if not (isinstance(group_names, list) or
    #                 isinstance(group_names, tuple)):
    #             group_names = tuple(group_names)
    #         group_ids = self.get_groupid(names=group_names)
    #     elif globus_groups is None and only_top_level:
    #         log.debug("Getting only top level group")
    #         group_ids = self.get_groupid(names=config["globus"]["root_group"])
    #     elif globus_groups is not None and group_names is not None:
    #         group_ids = self.get_groupid(groups=globus_groups,
    #                                      names=group_names)
    #     elif globus_groups is not None and group_names is None:
    #         group_ids = self.get_groupid(groups=globus_groups)
    #     elif globus_groups is not None and only_top_level:
    #         group_ids = self.get_groupid(globus_groups,
    #                                      config["globus"]["root_group"])
    #     log.debug("Looping through groups")
    #     # Loop though selected groups
    #     for group_id, group in group_ids.iteritems():
    #         if (no_top_level and
    #            group["name"] == config["globus"]["root_group"]):
    #             continue
    #         # Getting members
    #         try:
    #             headers, response = client.get_group_members(group_id)
    #         except socket.timeout:
    #             log.error(("Globus Nexus Server "
    #                        "response timed out. Skipping."))
    #             time.sleep(5)
    #             continue
    #         log.debug("Looping through users for group %s",
    #                   group["name"])    
    #         # for member in response['members']:
    #         #     if not member or member['status'] != 'active':
    #         #         continue
    #         #     username = str(member['username'])
    #         # filter by globus id and weird usernames
    #         globus_ids = [str(member['username'])
    #                       for member in response['members']
    #                       if member and member['status'] == 'active']
    #         non_globus_ids = [str(member['username'])
    #                           for member in response['members']
    #                           if (member and
    #                               member['status'] == 'active' and
    #                               "@" in member["username"]
    #         if get_user_profile:
    #                 try:
    #                     user_info = client.get_user(username)
    #                 except socket.timeout:
    #                     # if we time out, pause and resume, skipping current
    #                     log.error(("Socket timed out. Waiting for 5 seconds. "
    #                                "User %s was skipped") % username)
    #                     time.sleep(5)
    #                     continue
    #             else:
    #                 user_info = member
    #             if group["name"] in self.group_members:
    #                 self.group_members[group["name"]]["members"].append(
    #                     user_info)
    #                 self.group_members[group["name"]]["usernames"].append(username)
    #             else:
    #                 self.group_members[group["name"]] = {
    #                     "members": [user_info],
    #                     "usernames": [username],
    #                     "group": group}
    #             if (group["name"] != config["globus"]["root_group"] or
    #                 only_top_level):
    #                 self.member_group[username] = {
    #                     "user_profile": user_info,
    #                     "group_id": group_id,
    #                     "group_name": group["name"],
    #                     "group": group,
    #                     "top_group": (group["name"].split(".")[0]
    #                                   if not "project" in group["name"]
    #                                   else "osg")}
    #     return self.group_members, self.member_group

