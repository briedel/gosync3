# GOSync3

This is the replacement for the current GOSync. It is based on the [Globus SDK](http://globus-sdk-python.readthedocs.io/en/latest/), a [Globus SDK-based Globus Nexus Client](https://github.com/sirosen/globus-nexus-client/tree/master/globus_nexus_client), and puppet/hiera to create and manage UNIX users and groups. The main tasks of these classes and scripts is to interact with the GlobusID and Globus Groups database through their RESTful API and manage the JSON file that puppet/hiera require for creating and managing user accounts. 

The old GOSync was based on the [Globus Nexus Python library](https://github.com/globusonline/python-nexus-client). The Globus Nexus Python library has been official deprecated and functionality, such as accessing a user's GlobusID, will disappear over time. There was a GOSync2, however, it was still based on the Globus Nexus Python library and Globus is moving to an OAuth2-based model for all authentication and access to a user's GlobusID. We abandoned it after this change. 

Important notes READ BEFORE USING:

* This is a BETA. It does not have all the necessary features, like creating a group in Globus, to act as a full replacement yet.
*  This version uses Globus Nexus client based on the Globus SDK created by Stephen Rosen. This is not an official product of the Globus team. It is maintained though.

## Prerequisites

GOSync3 requires two Python packages:

```
globus-sdk[jwt]>=1.0,<2.0
globus-nexus-client
```

`globus-sdk[jwt]>=1.0,<2.0` is the Globus SDK including the JSON Web Token library. This is necessary to interact with Globus Auth and be able to do token introspection. `globus-nexus-client` is an implementation of the Nexus client using the Globus SDK. It is not an official Globus product, but supported by one of the authors (Stephen Rosen) of the Globus SDK.

In addition to the Python packages, one will need a Globus Confidential "app" that:

* Includes the correct scopes: `openid`, `profile`, `email`, `urn:globus:auth:scope:auth.globus.org:view_identity_set`, `urn:globus:auth:scope:auth.globus.org:view_identities`, `urn:globus:auth:scope:transfer.api.globus.org:all`, 
`urn:globus:auth:scope:auth.globus.org:view_ssh_public_keys`. Scopes can be thought of as permissions that the user has to agree to authenticate with the app.
* Is allowed to use the Group scopes. This requires filing a ticket with Globus to get the app ID added to the system.
* Has the correct redirection URLs (this depends on the website you are running)
* Requires the GlobusID as an identity provider,
* Has a secret associated with the app. 

For more details, please see the [Globus SDK documentation](http://globus-sdk-python.readthedocs.io/en/latest/tutorial/#step-1-get-a-client). 

## Assumptions

Following assumptions are made in the code:

* All users are part of the `connect` Globus Group
* The `connect` user is an `admin` or `manager` in all relevant groups

## Configuration

The configuration is a JSON file for ease of parsing it as a dictionary. The minimal configuration needed:

```
{
  "users": {
    "passwd_file": <passwd_file_to_be_used>
    "default_group": <default_group for users>
  },
  "groups": {
    "group_file": <group_file_to_be_used>
  },
  "globus": {
    "groups": {
      "root_group": <root_group>,
      "root_group_uuid": <root_group_globus_uuid>
    },
    "root_user": {
      // root user should only have admin or manager roles in the groups
      "roles": [
        "admin",
        "manager"
      ],
      "username": <root_user>,
      "secret": <root_user_passwd>,
      "auth_refresh_token": <root_user_globus_auth_token_for_app>,
      "nexus_refresh_token": <root_user_globus_nexus_token_for_app>
    },
    "user": {
      // regular user may have any role in a group
      "roles": [
        "member",
        "admin",
        "manager"
      ]
    },
    "app": {
      "scopes": [
        "openid",
        "profile",
        "email",
        "urn:globus:auth:scope:auth.globus.org:view_identities",
        "urn:globus:auth:scope:transfer.api.globus.org:all",
        "urn:globus:auth:scope:auth.globus.org:view_identity_set",
        "urn:globus:auth:scope:nexus.api.globus.org:groups"
      ],
      "client_id": <globus_app_id_as_string>,
      "client_secret": <globus_app_secret_as_string>
    }
  },
  "connect_db": {
    "db_file": <json_file_to_be_used_as_connect_db>
  }
}
```

This JSON object will be parsed into a Python dictionary and will be passed to the various classes.

## Globus Interface - `globus_db.py`

The class `globus_db` is meant as a one-stop shop for for retrieving information from the Globus ID and Globus Groups service. Please note that being able to `PUT` and `PUSH` information into Globus Groups is possible through the Nexus interface, but needs to be thoroughly tested before those methods will be available.

The class requires a configuration dictionary and an `connect_db` object. The configuration dictionary is explained above. The `connect_db` is needed to retrieve the the refresh tokens for users and allow of to check for changes in group membership, i.e. if users were added or removed from a group.

The class is split into four sections: client methods, group methods, group membership methods, and user methods.

### Client Methods and some explanation about various Globus tokens

The client methods are for getting the different types of clients needed to interact with GlobusID through Globus Auth and Globus Groups through Globus Nexus. There are two main clients used: Globus Auth client and Globus Nexus client. The Globus Auth client is for interacting with the user's GlobusID, i.e get the user profile in GlobusID. The Globus Nexus client is for interacting with a user's Globus Groups and their Globus Groups's profile.

The clients can be authenticated using Globus Auth tokens or Globus Online Auth legacy tokens. The latter will be referred to as legacy tokens from here on out. Tokens can be thought of as randomly generated passwords that encode the user's identity and the application's permission level.

Globus Auth tokens are OAuth2 tokens. OAuth2 gives the user and the authorization server the explicit power to reject or limit (either in time or scope) an application's access, to the user's information. It also moves large parts of the authentication process from the resource provider to an authentication provider, which allows for better separation between resources and authentication. For more details please visit [An introduction to OAuth2](https://www.digitalocean.com/community/tutorials/an-introduction-to-oauth-2). 

The Globus Auth tokens are split into three different types: Auth, Transfer, and Nexus. One will receive one, two, or all three, when a user authenticates against the app depending on an app's scopes, i.e. requested permissions. With the app created in the prequesities one will receive all three tokens. Auth tokens are meant for retrieving a user's information from Globus ID, i.e. linked identities, SSH keys, etc. Transfer tokens are for initiating Globus transfers on behalf of the user. Nexus tokens are for authorizing against the Globus Groups service to allow viewing a user's group membership. The Nexus tokens do not allow to view a user's Globus groups profile through a call to the user's Globus Nexus profile, i.e. the group-specific custom fields and the user identity, directly. This due to the Nexus group scope not having the permissions to view the user's GlobusID. This can be circumvented by through accessing the profile through the groups interface instead. I know... Please note that Nexus tokens are special. They are not officially available, one has to request access to the "group" scopes from Globus. 

Globus Auth tokens expire after some time, usually within 10 minutes, i.e. you as the application only have a limited amount of time to retrieve the desired information out of Globus. To be able to repeatedly authenticate with Globus Auth, one can request "refresh tokens". These tokens are valid until the user revokes an app's permission. These are required for GOSync3.

The individual methods are self-explanatory:

* `get_tokens`: Returns a user's tokens from the `connect_db` or retrieves the tokens from the configuration file for the root user.
* `get_legacy_client`: Returns a user's Nexus client that has been authenticated using legacy Globus Online Auth token, i.e. the user's username/password.
* `get_globus_client`: Returns the user's Globus Auth and Globus Nexus client authenticated using the user's refresh tokens. 

### Group Methods

The group methods currently only implement a `GET` from Globus Groups. There are two ways to access all groups associated with `connect`. The first is to the retrieve the group tree for the root group, named `connect`. The second is to retrieve all groups associated with the root user, also named `connect`. 

In GOSyn3, we are using the second method. There is a method to retrieve the group tree, but it is unused at the moment. The `get_group()` and `get_groups()` method simply filter the `all_groups` list for the desired group(s). `get_all_groups()` is the method that uses the root user's credentials to determine groups in which the root user, `connect`, is and `admin` or `manager`. The distinction between between being `admin`, `manager`, or `member` is important here. It filters the groups that are returned by Globus Nexus. The `connect` user will always be an `admin` or `manager` in a subgroup, while a user might be a `admin`, `manager`, or `member`. The root user is a `member` of some groups that are not associated with the Connect instances. 

In addition there is a `check_new_members()` methods at is currently used. It allows to filter the group list to those groups that have recently added members. 

### Group Membership Methods

The workflow for retrieving a user's group membership depends on the authentication method used. In a purely Globus Auth-based workflow, one would retrieve a user's group membership by using their tokens and calling `list_groups()` from the client. This is done in the function `get_user_groups_auth()`.

At the moment, we only have tokens for the `connect` user. To work around this, GOsync3 tries to generate a mapping of group to users first and then inverts that mapping, see function `get_user_groups_no_tokens()`. It retrieves the list of all groups associated with the `connect` and then determines the group members for every group. Using `_invert_dict_list_values()`, the group-to-users mapping is then inverted to the user-to-groups mapping. 

`get_group_members()` simply returns the users for a given group. This has to be done using the group's Globus UUID. A mapping of Globus group name to Globus group UUID is in the works. 

### User Methods

The user methods allow one to retrieve more information about user, i.e. query Globus for the user's "user information" and manipulate the Globus output in a more easily digestible patterns. 

`get_user_info()` is a specialization of `get_user_groups_profile()`. It allows to get the a user's profile, i.e. username, SSH key, group-specific information, full name, e-mail, through Globus Nexues. `get_user_info()` is specialization in the sens that it uses the root group user profile rather than specific group's profile as needed by `get_user_groups_profile()`.

`get_all_users()` simply grabs all the users in the root group and then queries Globus Groups for the user's profile. `_invert_dict_list_values()` allows you to invert the group to users mapping to a user to groups mapping.

## Puppet/Hiera Interface - `connect_db.py`

In this case, we are using the JSON file needed by puppet/hiera as a database. This is suboptimal, but it will do for now. The information source for puppet/hiera can be replaced by a real DB later on. Some of the information, i.e. UNIX ids, stored in the JSON file at the moment will be needed to populate a database down the road anyway. 

The puppet/hiera interface, i.e `connect_db()`, is a thin layer of the JSON object that puppet/hiera uses to provision user accounts. It reads a previous version of the JSON object, and produces a `users` and `groups` dictionary and a `uids` and `gids` list. These four objects contain all the necessary information to be able add new groups and users to the JSON object passed to puppet/hiera.

The `users` and `groups` dictionaries are made up of sub-dictionaries. Holding the information for each user and group, respectively. The `users` dictionary is a mapping of username to user information. In our case this is:

```
{
    "auth_refresh_token": # user's Globus Auth refresh token
    "comment": 
    "email": # user's emails
    "gid": # default group for passwd file
    "manage_group": # puppet/hiera config parameter
    "nexus_refresh_token": # user's Globus Nexus refresh token
    "shell": # default user shell
    "ssh_keys": # SSH key dictionary, explained below
    "uid": # user's UNIX id
    "groups": # list of user's groups
}
```

The `groups` dictionary follows a similar pattern:

```
{
    "gid": # group UNIX ID
    "num_users": # Number if active user according to Globus
    "globus_uuid": # Groups Globus UUID
}
```

Some of the methods in this class are self-explanatory:

* `add_group`: Add a new group to the `groups` dictionary
* `add_user`: Add a new user to the `users` dictionary
* `get_user`: Retrieve the user information by username
* `get_group`: Retrieve the group by group name
* `new_unix_id`: This will generate a new UNIX id by incrementing the maximum ID or setting it to 100000 for both groups and users
* `get_member_count`: Retrieve the group's active member count
* `get_auth_token`: Retrieve user's Globus Auth refresh token
* `get_nexus_token`: Retrieve user's Globus Nexus refresh token
* `get_globus_tokens`: Retrieves user's Globus Auth and Nexus refresh tokens
* `remove_unicode`: Remove unicode characters from a user's name. This can cause problems when generating a passwd file or trying to serialize a JSON file.
* `commit_old_version`: In the spirit of old GOSync, we commit the JSON file to Gitlab, so puppet/hiera can grab it from there
* `write_db`: Write the JSON object out.

The `decompose_sshkey` method is necessary because of the format that puppet/hiera wants the SSH key in. A typical SSH key is formatted as follows:

```
<encryption_type> <public_key> <idenitifier>

```

where the `<encryption_type>` is the type of SSH key, i.e. ssh-rsa, `<public_key>` is the actual key portion of an SSH key, and `<idenitifier>` is an optional identifier that is usually `<username>@<network_hostname>` of the machine the key pair was generated on. 

Puppet/hiera wants the key in this JSON object:

```
{
    "<identifier>":
    {
        "type": <encryption_type> # Encryption type, i.e. ssh-rsa, ssh-dsa
        "key": <public_key> # Key part
    }
}
```

This requires to split the key. Unfortunately, not all keys have the identifier. In those cases it is replaced with the user's email address. This will not affect operations.

## Future Plans

### `PUT` and `PUSH` Methods for Globus Interface

To create groups in Globus Groups, we will need to implement `PUT` and `PUSH` methods The `NexusClient` already has these, but they are untested. I will need to test them before I can sanction them. I also want to standardize all information that is stored in Globus Groups for all the groups. Currently there are several different formats. 

### Moving connect DB to a real DB

The data volume is not that large and the JSON file is sufficient to store all the information. Down the road, we might want split from Globus and at this point we need to retrieve all the data from Globus. Storing this data would need a database.

### Multiple Connect Globus Apps

Branded websites in Globus are mapped one-to-one to a specific Globus App. To have different branded website for the various connect instances, we would need multiple Globus Apps. Tokens are app-specific, so for users that are members of multiple connect instances, for example CI Connect and OSG Connect, we will need to keep track of different refresh tokens and apps that they are associated with. 