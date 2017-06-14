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
                 connect_db=None):
        """
        Intiliazer
        Args:
            config (dict): Configuration parameters
            get_members (bool): Get the members of the groups
        """
        if config is None:
            log.fatal(("No config provided. "
                      "Please make sure to supply your own!"))
            raise RuntimeError()
        self.config = config
        if not isinstance(self.config, dict):
            log.fatal("Config is not dict")
            raise RuntimeError()
        if connect_db is None:
            log.fatal("No connect_db object provided")
            raise RuntimeError()
        self.connect_db = connect_db
        self.all_groups = None

    """
    Globus Client methods
    """

    def get_tokens(self, username):
        """
        Gets the correct auth and nexus tokens for the users

        Args:
            username (str): User's GlobusID username

        Returns:
            auth_token (str): Globus Auth token
            nexus_token (str): Globus Nexus token
        """
        log.debug("Getting token for user: %s", username)
        # Depending on user we get the tokens differently
        # Connect user from the config file
        # Everyone else from the database
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
            auth_token, nexus_token = self.connect_db.get_globus_tokens(
                username)
        return auth_token, nexus_token

    def get_legacy_client(self, username, password):
        """
        Gets the Nexus Client using the username/password combination

        Args:
            username (str): User's GlobusID username
            password (str): User's GlobusID password

        Returns:
            auth_token (str): Globus Auth token
            nexus_token (str): Globus Nexus token
        """
        # Get the legacy Globus Auth Nexus token using the username/password
        nc = NexusClient(
            authorizer=globus_sdk.BasicAuthorizer(username, password))
        legacy_token = LegacyGOAuthAuthorizer(nc.get_goauth_token())
        # Creating a Nexus client with the legacy token
        nc_legacy = NexusClient(
            authorizer=legacy_token)
        return nc_legacy

    def get_globus_client(self, username=None):
        """
        Get Globus SDK RESTful clients

        Args:
            username (str): User's GlobusID username

        Returns:
            auth_client (Globus SDK Client): Globus Auth RESTful client
            nexus_client (Globus Nexus Client): Globus Auth-based RESTful
                                                Globus Nexus client
        """
        if username is None:
            username = self.config["globus"]["root_user"]["username"]

        log.debug("Getting Globus SDK Auth and Nexus client for user %s",
                  username)

        # Setting up Globus SDK client
        client_id = self.config["globus"]["app"]["client_id"]
        client_secret = self.config["globus"]["app"]["client_secret"]
        confidential_client = globus_sdk.ConfidentialAppAuthClient(
            client_id, client_secret)

        # Getting Authorizers
        auth_token, nexus_token = self.get_tokens(username)
        auth_authorizer = globus_sdk.RefreshTokenAuthorizer(
            auth_token,
            confidential_client)
        nexus_authorizer = globus_sdk.RefreshTokenAuthorizer(
            nexus_token,
            confidential_client)

        auth_client = globus_sdk.AuthClient(authorizer=auth_authorizer)
        nexus_client = NexusClient(authorizer=nexus_authorizer)
        return auth_client, nexus_client

    """
    Group Methods
    """

    def get_group(self, group_name, get_summary=False):
        """
        Get information about single groups

        Args:
            group_name: Globus name of the group

        Returns:
            Group information for group_name
        """
        group = self.get_groups(group_name, get_summary=get_summary)
        return group[0]

    def get_groups(self, group_names=None, get_summary=False):
        """
        Get information about a list of groups

        Args:
            group_names (list): List of Globus group names

        Returns:
            list: List with group information
        """
        if self.all_groups is None:
            all_groups = self.get_all_groups(get_summary=get_summary)
        if isinstance(group_names, six.string_types):
            group_names = [group_names]
        elif group_names is None:
            return all_groups
        ### TODO: what about number of active users
        groups = [group for group in all_groups
                  if group["name"] in group_names]
        return groups

    def get_all_groups(self, get_summary=False, update=False):
        """
        Get all groups associated with the globus root user ("connect")

        Args:
            update (bool): Optional argument to allow to update the group list
                           in case that is desired
        """
        if self.all_groups is not None and not update:
            return self.all_groups
        # Use root user to get the groups associated with it, i.e. all groups
        # the root user it admin/manager of
        all_groups = self.get_user_groups(
            [self.config["globus"]["root_user"]["username"]],
            using_tokens=True, get_summary=get_summary)
        self.all_groups = all_groups[self.config[
            "globus"]["root_user"]["username"]]
        return self.all_groups

    def get_roles(self, username=None):
        """
        Getting the user roles in a Globus group for a username

        Args:
            username (str): Optional argument of the user's username

        Returns:
            roles (list): List of possible user roles in a Globus group
        """
        if username is None:
            username = self.config["globus"]["root_user"]["username"]
        roles = (self.config["globus"]["root_user"]["roles"]
                 if username == self.config["globus"]["root_user"]["username"]
                 else self.config["globus"]["user"]["roles"])
        return roles

    def get_group_tree(self, username=None,
                       root_group_uuid=None,
                       depth=3, flatten_tree=False):
        """
        Get Globus group tree

        Args:
            username (string): username to use to populate group trees
            root_group_uuid (string): Root group to use for the search
            depth (int): How deep in the tree we need to look
        Returns:
            tree (dict with nested lists): Dictionary with a nested list
        """
        auth_client, nexus_client = self.get_globus_client(username=username)
        if root_group_uuid is None:
            root_group_uuid = self.config["globus"]["groups"][
                "root_group_uuid"]
        roles = self.get_roles(username)
        tree = nexus_client.get_group_tree(root_group_uuid,
                                           depth=depth,
                                           my_roles=roles)
        return tree

    def check_new_members(self, group_name, group_count):
        """
        Checking whether a group as new members

        Args:
            group_name (string): Group name to be checked
            group_count (int): How many users are currently in the group

        Returns:
            Bool whether the membership count changed
        """
        connect_member_count = self.connect_db.get_member_count(group_name)
        return (connect_member_count == group_count)

    def add_group(self, project_file, group_parent=None,
                  username=None):
        """
        Adding group to Globus Groups through the Nexus API

        Args:
            project_file (string): Text file with project description
            group_parent (string): Optional parent group for group that
                                   is being added
            username (string): Optional user that is admin of the group
        """
        if username is None:
            username = self.config["globus"]["root_user"]["username"]
        auth_client, nexus_client = self.get_globus_client(username=username)
        group_name, description = self.parse_project_file(project_file)
        # Setting the parent group, by default we need to hang off the
        # connect group
        if group_parent is None:
            group_parent = self.config["globus"]["groups"]["root_group"]
        else:
            group_name = (".").join([group_parent, group_name])
        # Getting UUID to assign parenthood
        group_parent_uuid = self.connect_db.get_group(
            group_parent)["globus_uuid"]
        nexus_client.create_group(group_name, description,
                                  parent=group_parent_uuid)

    def parse_project_file(self, project_file):
        """
        Parse a project file and convert it into the right format, i.e. HTML
        for Globus Groups

        Args:
            project_file (string): File with project information

        Returns:
            project_name (string): Name of project to be added
            description (string): Project description in HTML
        """
        project_name = None
        lines = []
        with open(project_file, "rt") as f:
            for line in f:
                # Finding the project name
                if "Short Project Name" in line:
                    project_name = line.split(":")[-1].strip(" ").rstrip("\n")
                # Making things HTML compliant - Replace \n to <br>
                line = line.replace("\n", "<br>")
                lines.append(line)
        description = ("").join(lines)
        if not project_name:
            log.fatal(('No "Short Project Name" provided in project file. '
                       'Cannot generate a Globus Group without one'))
            raise RuntimeError()
        return project_name, description

    """
    Group Membership Methods
    """

    def get_user_groups(self,
                        usernames=None, using_tokens=False, get_summary=False):
        """
        Get groups that a user is a member of using either Globus Auth or
        Globus Nexus

        Args:
            usernames (list of string or string): Optional List of users for
                                                  which to determine group
                                                  membership
            using_auth (bool): Optional whether to use Globus Auth or Nexus

        Returns:
            membership (dict): Mapping of user to list of Globus Groups
        """
        if isinstance(usernames, six.string_types):
            usernames = [usernames]
        elif usernames is None:
            usernames = [self.config["globus"]["root_user"]["username"]]
        if using_tokens:
            membership = self.get_user_groups_auth(usernames,
                                                   get_summary=get_summary)
        else:
            membership = self.get_user_groups_no_tokens(usernames,
                                                        get_summary=get_summary)
        return membership

    def get_user_groups_auth(self, usernames, get_summary=False):
        """
        Get groups that a user is a member of using Globus Auth. This requires
        authenticating as the user using the refresh token.

        Args:
            usernames (list of string or string): Optional List of users for
                                                  which to determine group
                                                  membership

        Returns:
            membership (dict): Mapping of user to list of Globus Groups
        """
        membership = {}
        for user in usernames:
            auth_client, nexus_client = self.get_globus_client(
                username=user)
            roles = self.get_roles(user)
            groups = nexus_client.list_groups(
                # fields="id,name",
                for_all_identities=True,
                include_identity_set_properties=True,
                my_roles=roles)
            if get_summary:
                groups = [nexus_client.get_group(grp["id"]).data
                          for grp in groups]
            membership[user] = groups
        return membership

    def get_user_groups_no_tokens(self, usernames, get_summary=False):
        """
        Get groups that a user is a member of using Globus Nexus. We cannot
        authenticate as the user unless we have their password. Need to
        authenticate as the root user ("connect") and the loop through the
        groups to get groups to members mapping. That mapping is then inverted

        TODO: Do something about the group summary

        Args:
            usernames (list): List of usernames

        Returns:
            member_groups (dict): Mapping of username to list of groups
        """
        group_members = {}
        for group in self.get_all_groups(get_summary=get_summary):
            group_members[group["name"]] = self.get_group_members(
                group["id"],
                only_usernames=True)
        member_groups = self._invert_dict_list_values(group_members)
        if usernames != [self.config["globus"]["root_user"]["username"]]:
            member_groups = {member: groups
                             for member, groups in member_groups.iteritems()
                             if member in usernames}
        return member_groups

    def get_group_members(self,
                          group_id,
                          get_user_summary=False,
                          only_usernames=False):
        """
        Getting the "active" group members for given group

        Args:
            group_id (string): Globus UUID of the group in question
            get_user_summary (bool): Optionally, get Globus Nexus user profile
            only_usernames (bool): Optionally, only return the username of the
                                   group name

        Returns:
            group_members (list): "Active" members for certain group
        """
        auth_client, nexus_client = self.get_globus_client()
        group_members = nexus_client.get_group_memberships(group_id).data

        def restrict_users(member):
            """
            Need to throw out "invited" or removed users and those with the
            wrong username

            Args:
                Globus member profile

            Returns:
                Bool
            """
            return (member["status"] == "active" and
                    "@" not in member["username"])

        if get_user_summary:
            group_members = [self.summarize_user(member)
                             for member in group_members["members"]
                             if restrict_users(member)]
        elif only_usernames:
            group_members = [member["username"]
                             for member in group_members["members"]
                             if restrict_users(member)]
        else:
            group_members = [member for member in group_members["members"]
                             if restrict_users(member)]
        return group_members

    """
    User Methods
    """

    def get_user_info(self, username):
        """
        Get the Globus groups user profile for a the user.

        Args:
            username (str): User's username

        Returns:
            user_data (dict): User data stored in Globus Nexus
        """
        user_data = self.get_user_groups_profile(
            username=username,
            group_id=self.config["globus"]["groups"]["root_group_uuid"])
        return user_data

    def get_user_groups_profile(self, username=None, group_id=None):
        if group_id is None:
            group_id = self.config["globus"]["groups"]["root_group_uuid"]
        if None in self.connect_db.get_globus_tokens(username):
            auth_client, nexus_client = self.get_globus_client()
        else:
            auth_client, nexus_client = self.get_globus_client(
                username=username)
        user_data = nexus_client.get_user_groups_profile(
            group_id, username).data
        return user_data

    def summarize_user(self, user, connect_db=True):
        """
        Format the Globus user profile output into a flatter format, i.e.
        removing unnecessary fields and flatting the "custom fields"
        into the profile

        Args:
            user (dict): Globus Nexus user dictionary
            connect_db (bool): Optional argument whether to change the format
                               for the connect db or not

        Returns:
            new_member_profile (dict): Reformatted member profile
        """
        new_member_profile = {}
        member_profile = self.get_user_info(user["username"])
        required_keys = ["username", "ssh_pubkeys", "custom_fields",
                         "fullname", "email", "identity_id"]
        for k, v in member_profile.iteritems():
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
        """
        Getting a list of all users with and without group membership

        Args:
            get_user_groups (bool): Optional argument to add the user's groups
                                    to the profile

        Returns:
            members (list): List of member profiles
        """
        members = self.get_group_members(
            self.config["globus"]["groups"]["root_group_uuid"],
            get_user_summary=True)
        if get_user_groups:
            ### Need to improve this.... looping over the members twice
            ### one time should be sufficient.... mostly a restriction of
            ### using nexus
            user_groups = self.get_user_groups()
            for member in members:
                member["groups"] = user_groups[member["username"]]
        return members

    def _invert_dict_list_values(self, dic):
        """
        Inverting a dict of {key: list of values} to {value: list of keys}

        Args:
            dic (dict): Dict {key: list of values} to be inverted

        Returns:
            dict: Inverted dict with {value: list of keys}
        """
        inv_dic = {x: list(t[1] for t in group)
                   for (x, group) in groupby(
                        sorted(((j, k) for k, v in dic.items() for j in v),
                               key=itemgetter(0)), key=itemgetter(0))}
        return inv_dic
