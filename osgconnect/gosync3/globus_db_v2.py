from __future__ import print_function
import logging as log
import globus_sdk
import six
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

    def get_tokens(self, username):
        print(username)
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
        print(username)
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

    def get_group_members(self):
        raise NotImplementedError()

    def get_group(self, group_name):
        raise NotImplementedError()

    def get_groups(self):
        auth_client, nexus_client = self.get_globus_client()
        roles = self.get_roles()
        groups = nexus_client.list_groups(
            fields="id,name",
            for_all_identities=True,
            include_identity_set_properties=True,
            my_roles=roles)
        return groups

    def get_user_info_for_db(self, username):
        raise NotImplementedError()

    def get_user_info(self, username):
        legacy_client = self.get_legacy_client(
            self.config["globus"]["root_user"]["username"],
            self.config["globus"]["root_user"]["secret"])
        return legacy_client.get_user(username).data

    def get_roles(self, username=None):
        if username is None:
            username = self.config["globus"]["root_user"]["username"]
        roles = (self.config["globus"]["root_user"]["roles"]
                 if username == self.config["globus"]["root_user"]["username"]
                 else self.config["globus"]["user"]["roles"])
        return roles

    def get_user_groups_membership(self, usernames):
        if isinstance(usernames, six.string_types):
            usernames = [usernames]
        membership = {}
        for user in usernames:
            auth_client, nexus_client = self.get_globus_client(
                username=user)
            roles = self.get_roles(user)
            membership[user] = nexus_client.list_groups(
                fields="id,name",
                for_all_identities=True,
                include_identity_set_properties=True,
                my_roles=roles)
        return membership

    def get_group_tree(self, username=None, root_group_uuid=None, depth=3):
        auth_client, nexus_client = self.get_globus_client(username=username)
        print(nexus_client)
        print(username)
        # print(nexus_client.get_user("connect"))
        if root_group_uuid is None:
            root_group_uuid = self.config["globus"]["groups"][
                "root_group_uuid"]
        roles = self.get_roles(username)
        tree = nexus_client.get_group_tree(root_group_uuid,
                                           depth=depth,
                                           my_roles=roles)
        return tree

    def get_group_members(self, group_id, username=None):
        auth_client, nexus_client = self.get_globus_client(username=username)
        group_members = nexus_client.get_group_memberships(self, group_id).data
        return group_members

    def check_new_members(self, group_name, group_count):
        return (self.check_group_membership_changes(group_name, group_count))

    def check_filters(self, term, filters):
        return (filters is not None and term not in filters)

    def check_group_membership_changes(self, group_name, globus_member_count):
        connect_member_count = self.connect_db.get_member_count(group_name)
        return (connect_member_count == globus_member_count)