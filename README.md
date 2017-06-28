# GOSync3

GOSync3 is the replacement for the original GOSync. It is based on the [Globus SDK](http://globus-sdk-python.readthedocs.io/en/latest/), the [Globus SDK-based Globus Nexus Client](https://github.com/sirosen/globus-nexus-client/tree/master/globus_nexus_client), and puppet/hiera to create and manage UNIX users and groups. The main tasks of these classes and scripts are to interact with the GlobusID and Globus Groups database through their RESTful API and manage the JSON file that puppet/hiera requires for creating and managing user accounts. 

The original GOSync is based on the [Globus Nexus Python library](https://github.com/globusonline/python-nexus-client). The Globus Nexus Python library has been officially deprecated. An improved version of the original GOSync, i.e. GOSync2, was under development. It was still based on the Globus Nexus Python library. The development was abandoned as Globus has moved to a OAuth2-based authentication model and access to a user's GlobusID.

Important notes READ BEFORE USING:

* This is a BETA. It does not have all the necessary features to act as a full replacement yet.
* This version uses Globus Nexus client based on the Globus SDK created by Stephen Rosen. This is not an official product of the Globus team. It is maintained though.

## Assumptions

Following assumptions are made in the code:
  
* All users are part of the `connect` Globus Group
* The `connect` user is an `admin` or `manager` in all relevant groups

## Work flow

The GOSync3 work flow is meant to operate without human intervention, i.e. as a `cron` job, besides the normal user approval process. At the moment, there is no connection between account applications and GOSync3. Hence, there is no way of knowing which user is new, updated his/her profile, or changed their group membership. This should change in the future, see the last section for details.

In the current work flow, GOSync3 retrieves all groups in which the `connect` user is an `Administrator` or `Manager`. The `connect` user acts like the root user in a UNIX operating system. In addition to the group name and the UUID assigned by Globus Groups, the number of active members is being fetched by querying the group's summary from Globus.  

For creating and updating users the work flow is more complicated. First, GOSync3 retrieves all users and their profile associated with the root group, i.e. `connect`. It is necessary to fetch the user profile because it contains the user's SSH key. To determine the the user's group membership, the the group to users mapping is generated by looping through all groups getting their group members. FRom this mapping a user to groups mapping is generated. With the necessary information in hand, it the user information in the JSON object is created or updated.

## Prerequisites

GOSync3 requires at least Python 2.7 and Python packages:

```
globus-sdk[jwt]>=1.0,<2.0
globus-nexus-client>=0.2.5
```

`globus-sdk[jwt]>=1.0,<2.0` is the Globus SDK including the [JSON Web Token (JWT)](https://jwt.io/) library. JWT is necessary to interact with Globus Auth and be able to do token introspection. `globus-nexus-client>=0.2.5` is an implementation of the Nexus client using the Globus SDK. It is not an official Globus product, but supported by one of the authors (Stephen Rosen) of the Globus SDK.

In addition to the Python packages, one will need a Globus Confidential application, see [here](https://docs.globus.org/api/auth/developer-guide/) for details, that:

* Includes the user-granted permissions ("scopes"):
    - `openid`
    - `profile`
    - `email`
    - `urn:globus:auth:scope:auth.globus.org:view_identity_set`
    - `urn:globus:auth:scope:auth.globus.org:view_identities`
    - `urn:globus:auth:scope:transfer.api.globus.org:all`
    - `urn:globus:auth:scope:auth.globus.org:view_ssh_public_keys`
* Is allowed to use the Group scopes. This requires filing a ticket with Globus to get the app ID added to the system
* Has the correct redirection URLs (this depends on the website you are running)
* Requires the GlobusID as an identity provider
* Has a secret associated with the application

For more details, please see the [Globus SDK documentation](http://globus-sdk-python.readthedocs.io/en/latest/tutorial/#step-1-get-a-client). 

## Configuration

The configuration is a JSON file for ease of parsing it as a dictionary. The minimal configuration needed is:

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

## Execute code

### Syncing User and Groups - `gosync_globus_auth.py`

Executing `gosync_globus_auth.py` will sync the users and groups from Globus. If you want to run with you own config: `./gosync_globus_auth.py --config /path/to/config`. If you want to increase the verbosity, default the program will not print out anything to screen, simply add the `-v` flag. To increase the verbosity, just add more `v`s, i.e. `-vvvv`.

### Adding Group - `add_connect_group.py`

To add a group to Globus Groups requires, a file formatted as provided by the OSG Connect Website, details below. With the groups project file, a group is added through executing `./add_connect_group.py --projectfile /path/to/file --parent <parent_group>`. The `--parent <parent_group>` is optional, but necessary to maintain the group tree structure and determine the correct group name in Globus. To pass your own configuration you will need to the `--config /path/to/new/config` option. There is also a verbosity flag, i.e. `-v`, `-vv`, and `-vvv`. 

## Globus Interface - `globus_db.py`

The class `globus_db` is meant as an interface to the Globus ID and Globus Groups services. Please note that being able to `PUT` and `PUSH` information into Globus Groups is possible through the Nexus interface. Currently, only the `PUT` for Globus Groups is supported.

The class requires a configuration dictionary and an `connect_db` object. The configuration dictionary is explained above. The `connect_db` is needed to retrieve the the refresh tokens for users and allow of to check for changes in group membership, i.e. if users were added or removed from a group.

The class is split into four sections: client methods, group methods, group membership methods, and user methods.

### Client Methods and some explanation about various Globus tokens

The client methods are for getting the different types of clients needed to interact with GlobusID through Globus Auth and Globus Groups through Globus Nexus. There are two main clients used: Globus Auth client and Globus Nexus client. The Globus Auth client is for interacting with the user's GlobusID, i.e get the user profile in GlobusID. The Globus Nexus client is for interacting with a user's Globus Groups and their Globus Groups's profile.

The clients can be authenticated using Globus Auth tokens or Globus Online Auth legacy tokens. Tokens can be thought of as randomly generated passwords that encode the user's identity and the application's permission level. Globus Online Auth legacy tokens will be referred to as legacy tokens from here on out. Legacy tokens should be avoided at all cost. They may not work down the road and are bad practice.

Globus Auth tokens are OAuth2 tokens. OAuth2 gives the user and the authorization server the explicit power to reject or limit (either in time or scope) an application's access, to the user's information. It also moves large parts of the authentication process from the resource provider to an authentication provider, which allows for better separation between resources and authentication. For more details please visit [An introduction to OAuth2](https://www.digitalocean.com/community/tutorials/an-introduction-to-oauth-2). 

The Globus Auth tokens are split into three different types: Auth, Transfer, and Nexus. One will receive one, two, or all three, when a user authenticates against the app depending on an app's scopes, i.e. requested permissions. With the app created in the prerequisites one will receive all three tokens. Auth tokens are meant for retrieving a user's information from Globus ID, i.e. linked identities, SSH keys, etc. Transfer tokens are for initiating Globus transfers on behalf of the user. Nexus tokens are for authorizing against the Globus Groups service to allow viewing a user's group membership. The Nexus tokens do not allow to view a user's Globus groups profile through a call to the user's Globus Nexus profile, i.e. the group-specific custom fields and the user identity, directly. This due to the Nexus group scope not having the permissions to view the user's GlobusID. This can be circumvented by through accessing the profile through the groups interface instead. I know... Please note that Nexus tokens are special. They are not officially available, one has to request access to the "group" scopes from Globus. 

Globus Auth tokens expire after some time, usually within 10 minutes, i.e. you as the application only have a limited amount of time to retrieve the desired information out of Globus. To be able to repeatedly authenticate with Globus Auth, one can request "refresh tokens". These tokens are valid until the user revokes an app's permission. These are required for GOSync3.

The individual methods are self-explanatory:

* `get_tokens`: Returns a user's tokens from the `connect_db` or retrieves the tokens from the configuration file for the root user.
* `get_legacy_client`: Returns a user's Nexus client that has been authenticated using legacy Globus Online Auth token, i.e. the user's username/password.
* `get_globus_client`: Returns the user's Globus Auth and Globus Nexus client authenticated using the user's refresh tokens. 

### Group Methods

#### Retrieving Group Infomation - `GET` Methods
There are two ways to access all groups associated with `connect`. The first is to the retrieve the group tree for the root group, named `connect`. The second is to retrieve all groups associated with the root user, also named `connect`. 

In GOSyn3, we are using the second method. There is a method to retrieve the group tree, but it is unused at the moment. The `get_group` and `get_groups` method simply filter the `all_groups` list for the desired group(s). `get_all_groups` is the method that uses the root user's credentials to determine groups in which the root user, `connect`, is an `admin` or `manager`. The distinction between between being `admin`, `manager`, or `member` is important here. It filters the groups that are returned by Globus Nexus. The `connect` user will always be an `admin` or `manager` in a subgroup, while a user might be a `admin`, `manager`, or `member`. The root user is a `member` of some groups that are not associated with the Connect instances. 

In addition there is a `check_new_members` methods at is currently used. It allows to filter the group list to those groups that have recently added members. 

#### Adding Group Information - `POST` Methods

GOSync3 has the ability to add groups to Globus Groups. This is done through the `add_group` and `parse_project_file` methods. Adding a group is done through the `add_groups` method. It calls the `globus-nexus-client`'s `create_group` method to create the group with name and description provided through the project description text file, details on this below. Optionally, one can pass a parent group to the method. It is strongly recommended to provide a parent group, without a group the group will be assumed to be a top-level group below the root `connect` group. 

The project description text file should follow the format of the form on the [New Project section on the OSG Connect website](http://osgconnect.net/newproject). This will provide a text file of the following format:

```
Your Name: 
Your Email Address: 
Project Name: 
Short Project Name: 
Field of Science: Evolutionary 
Field of Science (if Other): 
PI Name: 
PI Email:
PI Organization:
PI Department:
Join Date: 
Sponsor: 
OSG Sponsor Contact: 
Project Contact: 
Project Contact Email: 
Telephone Number: 
Project Description:
```

From this the only required field is the "Short Project Name". The value will be used as the group name in Globus Groups. 

`parse_project_file` parses the project file, determines the expected name of the group, and converts the plain text to HTML-formatted text. The project name is determined from the "Short Project Name" in the project file and the parent group. The format of the Globus Groups name is `<parent_group>.<short_project_name`. To make the text HTML-formatted, the only action is to converted newline characters (`\n`) to `<br>`.

### Group Membership Methods

The work flow for retrieving a user's group membership depends on the authentication method used. In a purely Globus Auth-based workflow, one would retrieve a user's group membership by using their tokens and calling `list_groups` method from the Nexus client. This is done in the function `get_user_groups_auth`.

At the moment, we only have tokens for the `connect` user. To work around this, GOSync3 tries to generate a mapping of group to users first and then inverts that mapping, see function `get_user_groups_no_tokens`. It retrieves the list of all groups associated with the `connect` user and then determines the group members for every group. Using `_invert_dict_list_values`, the group-to-users mapping is then inverted to the user-to-groups mapping. 

`get_group_members` simply returns the users for a given group. This has to be done using the group's Globus UUID. A mapping of Globus group name to Globus group UUID is provided by the `connect_db`.

### User Methods

The user methods allow the user to retrieve more information about user, i.e. query Globus for the user's "user information" and manipulate the Globus output in a more easily digestible patterns. 

`get_user_info` is a specialization of `get_user_groups_profile`. It allows to fetch the a user's profile, i.e. username, SSH key, group-specific information, full name, e-mail, through Globus Groups. `get_user_info` is specialization in the sense that it uses the root group user profile rather than specific group's profile as needed by `get_user_groups_profile`.

`get_all_users` retrieves all the users in the root group and then queries Globus Groups for the user's profile. `_invert_dict_list_values` allows you to invert the group to users mapping to a user to groups mapping.

## Puppet/Hiera Interface - `connect_db.py`

In this case, the JSON file used by puppet/hiera is used as a user database. This is suboptimal. It will allow us to quickly deploy GOSync3. The information source for the puppet/hiera JSON file can be replaced by a real DB later on. Some of the information, i.e. UNIX ids, stored in the JSON file will be needed to populate a replacement database.

The puppet/hiera interface, i.e `connect_db`, is a thin layer of the JSON object that puppet/hiera uses to provision user accounts. It reads a previous version of the JSON object, and produces a `users` and `groups` dictionary and a `uids` and `gids` list. These four objects contain all the necessary information to be able add new groups and users to the JSON object passed to puppet/hiera.

The `users` and `groups` dictionaries are made up of sub-dictionaries. Holding the information for each user and group, respectively. The `users` dictionary is a mapping of username to user information, such that:

```
{
    "auth_refresh_token": # user's Globus Auth refresh token
    "comment": # user's name
    "email": # user's emails
    "gid": # default group for passwd file
    "manage_group": # puppet/hiera config parameter
    "nexus_refresh_token": # user's Globus Nexus refresh token
    "shell": # default user shell
    "ssh_keys": # SSH key dictionary, explained below
    "uid": # user's UNIX id
    "groups": # list of user's groups,
    "connect_project":  # Initial connect project, typically osg.ConnectTrain
    "condor_schedd": # The condor schedd to pick on the login host
}
```

The `groups` dictionary follows a similar pattern. Mapping a group name to:

```
{
    "gid": # group UNIX ID
    "num_members": # Number if active user according to Globus
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
* `write_db`: Write the JSON object out. If a `email_file` is supplied in the config, it will also create a json file that maps the group users to their email addresses
* `set_user_nologin`: Set a user's shell to nologin, used in case they are no longer "active" in a Globus group
* `get_emails`: Get email for everyone or optionally for a given group
* `get_email`: Get email for a specific user

The `get_default_project` method is tries to guess a user's first OSG project for account reasons. If the user is a member of more than more than one sub-project we need to filter out any of the default ones. First, "osg.ConnectTrain" is removed. If there are still more than one projects, we filter out any project associated with a user school and any OSG project, if the user is a member of the other connect instances, i.e. SPT, ATLAS, CMS, and Duke. 

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

This requires to split the key according to the spaces it in. Unfortunately, not all keys have the identifier. In those cases it is replaced with the user's email address. This will not affect operations. There is a question though about overriding SSH keys. 

## Future Plans

### Work flow Improvements

There are three slow processes in the current work flow:

* Getting the group summary 
* Getting the user summary
* Getting the user group memberships

The first processes are slow because we have to query the Globus Groups database separately each piece of the group information: group profile, number of members, and group members, respectively. In addition, queries on the Globus side slow down as the group tree grows in size and as we add more groups the more queries we have to perform. Getting the user summary is a similarly expensive process because we have to query Globus for every user twice, once to get their general information, and another to get their SSH key.

One of the main steps to improve the efficiency requires to change the website to use OAuth2. This would allow us to operate on a per-user basis rather than on a per-group basis. In an idealized work flow, a user would sign up on the website. This sign up process would trigger the ability to retrieve the users identity (including their SSH key)and their Globus OAuth tokens, see below for more details on Globus OAuth tokens. With the identity and Globus token in hand, we can then query Globus for just the new user's group memberships. The first query would happen be default at sign up, while the group membership query would come after they are approved. The second query may have to be repeated several time. This is not wasted effort though, since we are waiting for human intervention. Similarly, we could trigger a Globus query of a given user's profile once they login. This would make updating the user information on our end dependent on user actions rather than us having to repeatedly query Globus for their information. Given that we most likely will never have tokens for all users, we will need operate in a hybrid mode, where the new user's are handled solely through the tokens, while older users will have still have to be kept up to date through the above described work flow. 

### `PUT` and `PUSH` Methods for Globus Interface

To create groups in Globus Groups, we will need to implement `PUSH` methods. The `NexusClient` already has these, but they are untested. I will need to test them before I can sanction them. I also want to standardize all information that is stored in Globus Groups for all the groups. Currently there are several different formats. 

### Moving connect DB to a real DB

The data volume is not that large and the JSON file is sufficient to store all the information. Down the road, we might want split from Globus and at this point we need to retrieve all the data from Globus. Storing this data would need a database.

### Multiple Connect Globus Apps

Branded websites in Globus are mapped one-to-one to a specific Globus App. To have different branded website for the various connect instances, we would need multiple Globus Apps. Tokens are app-specific, so for users that are members of multiple connect instances, for example CI Connect and OSG Connect, we will need to keep track of different refresh tokens and apps that they are associated with. 