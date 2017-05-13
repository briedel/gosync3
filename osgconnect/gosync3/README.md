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

`globus-sdk[jwt]>=1.0,<2.0` is the Globus SDK including the JSON Web Token library. This is necessary to interact with Globus Auth and be able to do the token introspection required to determine the user and group information. `globus-nexus-client` is an implementation of the Nexus client using the Globus SDK. It is not an official Globus product, but supported by one of the authors (Stephen Rosen) of the Globus SDK.

In addition to the Python packages, one will need a Globus Confidential "app" that:

* Includes the correct scopes: `openid`, `profile`, `email`, `urn:globus:auth:scope:auth.globus.org:view_identity_set`, `urn:globus:auth:scope:auth.globus.org:view_identities`, `urn:globus:auth:scope:transfer.api.globus.org:all`. Scopes can be thought of as permissions that the user has to agree to authenticate with the app.
* Is allowed to use the Group scopes. This requires filing a ticket with Globus to get the app ID added to the system.
* Has the correct redirection URLs (this depends on the website you are running)
* Requires the GlobusID as an identity provider,
* Has a secret associated with the app. 

For more details, please see the [Globus SDK documentation](http://globus-sdk-python.readthedocs.io/en/latest/tutorial/#step-1-get-a-client). 

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

The clients can be authenticated using Globus Auth tokens or Globus Online Auth legacy tokens. The latter will be referred to as legacy tokens from here on out. Tokens can be thought of as randomly generated passwords that encode the user's identßity and the application's permission level.

Globus Auth tokens are OAuth2 tokens. OAuth2 gives the user the explicit power to reject or limit (either in time or scope) an application's access, to the user's information. It also moves large parts of the authentication process from the resource provider to an authentication provider, which allows for better separation between resources and authentication. For more details please visit [An introduction to OAuth2](https://www.digitalocean.com/community/tutorials/an-introduction-to-oauth-2). 

The Globus Auth tokens are split into three different types: Auth, Transfer, and Nexus. One will receive one, two, or all three, when the user authenticates against the app depending on an app's scopes, i.e. requested permissions. Auth tokens are meant for retrieving a user's information from Globus ID, i.e. linked identities, SHH keys, etc. Transfer tokens are for initiating Globus transfers on behalf of the user. Nexus tokens are for authorizing against the Globus Groups service to allow viewing a user's group membership. The Nexus tokens do not allow to view a user's Globus groups profile through a call to the user's Globus Nexus profile, i.e. the group-specific custom fields and the user identity, directly. This due to the Nexus group scope not having the permissions to view the user's GlobusID. This can be circumvented by through accessing the profile through the groups interface instead. I know... Please note that Nexus tokens are special. They are not officially available, one has to request access to the "group" scopes from Globus. 

Globus Auth tokens expire after some time, usually within 10 minutes, i.e. you as the application only have a limited amount of time to retrieve the desired information out of Globus. To be able to repeatedly authenticate with Globus Auth, one can request "refresh tokens". These tokens are valid until the user revokes an app's permission. These are required for GOSync3.

<!-- The legacy tokens are tokens that were issued by Globus Online, specifically Globus Nexus, before the transition to an OAuth2-based model. Unlike, Globus Auth tokens they do not require any scopes and do not expire. They can be retrieved from Globus Nexus once a user authenticates against the service with their username and password. The authentication model is implicit from the user's perspective. By joining a given group, the user implicitly agrees to allow a privileged user, i.e. an `admin` or `manager`, to access their Globus Groups information and user profile. 

There is currently an issue with the permissions of the Globus Auth groups scope, i.e. the permission granted through a Nexus token. It does not allow the admin/manager of a group to get a users for profile from Globus Groups. One can only determine the group membership. Alternatively, one could use a user's refresh token, but those are only generate once a user logs in and are tied to a Globus "app".

To get around this permissions, GOSync3 has to use the the Globus Nexus client authenticated with a legacy Globus Online Auth token. This circumvents the Globus Auth scopes and allows direct access to Nexus. To get the legacy token, one has to login into the Nexus client using the Globus SDK's `BasicAuthorizer` using the root users username and password. From this login one can get the the legacy token using the `LegacyGOAuthAuthorizer`. Now a new Nexus Client using the `LegacyGOAuthAuthorizer` is created to gain access to the user information. This may not work in the future. Are you confused yet? -->

### Group Methods

The group methods currently only implement a `GET` from Globus Groups. There are two ways to access all groups associated with `connect`. The first is to the retrieve the group tree for the root group, named `connect`, inside Globus Groups. The second is to retrieve all groups associated with the root user, also named `connect`. 

In this case, we are using the second method. There is a method to retrieve the group tree, but it is unused at the moment. The `get_group` and `get_groups` method simply filter the `all_groups` list for the desired group(s). `get_all_groups` is the method that uses the root user's credentials to determine groups in which the root user, `connect`, is and `admin` or `manager`. The distinction between between being `admin`, `manager`, or `member` is important here. It filters the groups that are returned by Globus Nexus. The `connect` user will always be an `admin` or `manager` in a subgroup., while a user might be a 

### Group Membership Methods

The difference in operation between Globus Auth and Globus Nexus requires for different methods to determine the group membership of a user or to get the group members. In Globus Auth, one authenticates as the user through their refresh token and then queries Globus Groups as the user. This will result in a list of groups that the user is either an `admin`, `manager`, or `member`. Without this refresh token for every user, the only way to retrieve the 

### User Methods



## Puppet/Hiera Interface - `connect_db.py`


## Future Plans

### `PUT` and `PUSH` Methods for Globus Interface

### Moving connect db to a real DB

