from __future__ import print_function
import logging as log
import globus_sdk
import six
from itertools import groupby
from operator import itemgetter
from globus_nexus_client import NexusClient, LegacyGOAuthAuthorizer


class globus_db(object):
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
        # get legacy tokens, and "connect" user get_tokens
        self.legacy_client = self.get_legacy_client(
            self.config["globus"]["root_user"]["username"],
            self.config["globus"]["root_user"]["secret"])
        self.all_groups = None

    """
    Gloubus Client methods
    """

    def get_tokens(self, username):
        if username == self.config["globus"]["root_user"]["username"]:
            auth_token = self.config[
                "globus"]["root_user"]["auth_refresh_token"]
            nexus_token = self.config[
                "globus"]["root_user"]["nexus_refresh_token"]
        elif username == "briedel":
            auth_token = self.config[
                "globus"]["user"]["auth_refresh_token"]
            nexus_token = self.config[
                "globus"]["user"]["nexus_refresh_token"]
        else:
            auth_token = self.connect_db.get_auth_token(username)
            nexus_token = self.connect_db.get_nexus_token(username)
        return auth_token, nexus_token

    def get_legacy_client(self, username, password):
        nc = NexusClient(
            authorizer=globus_sdk.BasicAuthorizer(username, password))
        legacy_token = LegacyGOAuthAuthorizer(nc.get_goauth_token())
        nc_legacy = NexusClient(
            authorizer=legacy_token)
        return nc_legacy

    def get_globus_client(self, username=None):
        """
        Get Globus SDK-Nexus RESTful client

        Args:
            config: Configuration dict()

        Returns:
            client: Globus Nexus RESTful client
        """
        if username is None:
            username = self.config["globus"]["root_user"]["username"]

        client_id = self.config["globus"]["app"]["client_id"]
        client_secret = self.config["globus"]["app"]["client_secret"]
        confidential_client = globus_sdk.ConfidentialAppAuthClient(
            client_id, client_secret)

        auth_token, nexus_token = self.get_tokens(username)
        auth_authorizer = globus_sdk.RefreshTokenAuthorizer(
            auth_token,
            confidential_client)
        nexus_authorizer = globus_sdk.RefreshTokenAuthorizer(
            nexus_token,
            confidential_client)

        auth_client = globus_sdk.AuthClient(authorizer=auth_authorizer)
        nexus_client = NexusClient(authorizer=nexus_authorizer)
        log.debug("Got Globus Nexus client")
        return auth_client, nexus_client


    """
    Group Methods
    """

    def get_group(self, group_name):
        group = self.get_groups(group_name)
        return group[0]

    def get_groups(self, group_names=None):
        if self.all_groups is None:
            all_groups = self.get_all_groups()
        if isinstance(group_names, six.string_types):
            group_names = [group_names]
        elif group_names is None:
            return all_groups
        groups = [group for group in all_groups
                  if group["name"] in group_names]
        return groups

    def get_all_groups(self, update=True):
        if self.all_groups is not None and update:
            return self.all_groups
        all_groups = self.get_user_groups(
            [self.config["globus"]["root_user"]["username"]],
            using_auth=True)
        self.all_groups = all_groups[self.config[
            "globus"]["root_user"]["username"]]
        return self.all_groups

    def get_user_info_for_db(self, username):
        raise NotImplementedError()

    def get_user_info(self, username):
        return self.legacy_client.get_user(username).data

    def get_roles(self, username=None):
        if username is None:
            username = self.config["globus"]["root_user"]["username"]
        roles = (self.config["globus"]["root_user"]["roles"]
                 if username == self.config["globus"]["root_user"]["username"]
                 else self.config["globus"]["user"]["roles"])
        return roles

    def get_group_tree(self, username=None, root_group_uuid=None, depth=3):
        auth_client, nexus_client = self.get_globus_client(username=username)
        if root_group_uuid is None:
            root_group_uuid = self.config["globus"]["groups"][
                "root_group_uuid"]
        roles = self.get_roles(username)
        tree = nexus_client.get_group_tree(root_group_uuid,
                                           depth=depth,
                                           my_roles=roles)
        return tree

    """
    Group Membership Methods
    """

    def get_user_groups(self, usernames=None, using_auth=False):
        if isinstance(usernames, six.string_types):
            usernames = [usernames]
        #### TODO: NEED TO FIX THIS FOR NEXUS
        elif usernames is None:
            usernames = [self.config["globus"]["root_user"]["username"]]
        if using_auth:
            membership = self.get_user_groups_auth(usernames)
        else:
            membership = self.get_user_groups_nexus(usernames)
        return membership

    def get_user_groups_auth(self, usernames):
        membership = {}
        for user in usernames:
            auth_client, nexus_client = self.get_globus_client(
                username=user)
            roles = self.get_roles(user)
            membership[user] = nexus_client.list_groups(
                # fields="id,name",
                for_all_identities=True,
                include_identity_set_properties=True,
                my_roles=roles)
        return membership

    def get_user_groups_nexus(self, usernames):
        group_members = {}
        for group in self.get_all_groups():
            group_members[group["name"]] = self.get_group_members(
                group["id"],
                only_usernames=True)
        member_groups = self._invert_dict_list_values(group_members)
        if usernames != [self.config["globus"]["root_user"]["username"]]:
            member_groups = {member: groups
                             for member, groups in member_groups.iteritems()
                             if member in usernames}
        return member_groups

    def get_group_members(self, group_id,
                          username=None, get_user_summary=False,
                          only_usernames=False):
        auth_client, nexus_client = self.get_globus_client(username=username)
        group_members = nexus_client.get_group_memberships(group_id).data
        if get_user_summary:
            group_members = [self.summarize_user(member)
                             for member in group_members["members"]
                             if member["status"] == "active"]
        elif only_usernames:
            group_members = [member["username"]
                             for member in group_members["members"]
                             if member["status"] == "active"]
        else:
            group_members = [member for member in group_members["members"]
                             if member["status"] == "active"]
        return group_members

    def summarize_user(self, user, connect_db=True):
        new_member_profile = {}
        member_profile = self.get_user_info(user["username"])
        required_keys = ["username", "ssh_pubkeys", "custom_fields",
                         "fullname", "email", "identity_id"]
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
                    if connect_db:
                        if k == "fullname":
                            k = "name"
                        if k == "identity_id":
                            k = "globus_uuid"
                    new_member_profile[k] = v
            else:
                for sk, sv in v.iteritems():
                    if sk in new_member_profile.keys():
                        continue
                    new_member_profile[sk] = sv
        return new_member_profile

    def get_all_users(self, get_user_groups=False):
        members = self.get_group_members(
            self.config["globus"]["groups"]["root_group_uuid"],
            get_user_summary=True)
        if get_user_groups:
            ### Need to improve this.... looping over the members twice
            ### one time should be sufficient.... most a restriction of
            ### using nexes
            user_groups = self.get_user_groups()
            for member in members:
                member["groups"] = user_groups[member["username"]]
        return members

    def check_new_members(self, group_name, group_count):
        return (self.check_group_membership_changes(group_name, group_count))

    def check_filters(self, term, filters):
        return (filters is not None and term not in filters)

    def check_group_membership_changes(self, group_name, globus_member_count):
        connect_member_count = self.connect_db.get_member_count(group_name)
        return (connect_member_count == globus_member_count)

    def _invert_dict_list_values(self, dic):
        return {x: list(t[1] for t in group)
                for (x, group) in groupby(sorted(((j, k) for k, v in dic.items()
                                                  for j in v), key=itemgetter(0)),
                                          key=itemgetter(0))
                }
