#!/usr/bin/env python
from __future__ import print_function
import webbrowser
import argparse
import globus_sdk
from util import parse_config

parser = argparse.ArgumentParser()
parser.add_argument("--config", help="Config file",
                    dest="config_file", type=str)
args = parser.parse_args()

config = parse_config(args.config_file)

def do_native_app_authentication(config):
    client = globus_sdk.NativeAppAuthClient(config["Globus"]["client_id"])
    client.oauth2_start_flow_native_app(requested_scopes="openid email profile urn:globus:auth:scope:transfer.api.globus.org:all")

    url = client.oauth2_get_authorize_url()

    print('Native App Authorization URL: \n{}'.format(url))
    # if not is_remote_session():
    #     webbrowser.open(url, new=1)


# def get_globus_tokens(config):
#     """
#     Get Globus authenication tokens
#     """
#     client = globus_sdk.NativeAppAuthClient(config["Globus"]["client_id"])
#     # print(client.oauth2_refresh_token("6vVg3RpGdBgfuPXtEG7H6nOWy7AJAL"))
#     client.oauth2_start_flow_native_app()


#     authorize_url = client.oauth2_get_authorize_url()
#     print('Please go to this URL and login: {0}'.format(authorize_url))

#     # this is to work on Python2 and Python3 -- you can just use raw_input() or
#     # input() for your specific version
#     get_input = getattr(__builtins__, 'raw_input', input)
#     auth_code = get_input(
#         'Please enter the code you get after login here: ').strip()
#     token_response = client.oauth2_exchange_code_for_tokens(auth_code)
#     print(token_response)
#     # p
#     # globus_auth_data = token_response.by_resource_server['auth.globus.org']
#     # globus_transfer_data = token_response.by_resource_server['transfer.api.globus.org']

#     # # client.oauth2_refresh_token()

#     # # # most specifically, you want these tokens as strings
#     # auth_token = globus_auth_data['access_token']
#     # transfer_token = globus_transfer_data['access_token']

#     # return auth_token, transfer_token

# get_globus_tokens(config)


############################################################################

####
# FROM GLOBUS GITHUB
####

# get_input = getattr(__builtins__, 'raw_input', input)

# def do_native_app_authentication(client_id, redirect_uri,
#                                  requested_scopes=None):
#     """
#     Does a Native App authentication flow and returns a
#     dict of tokens keyed by service name.
#     """
#     client = NativeAppAuthClient(client_id=client_id)
#     client.oauth2_start_flow_native_app(requested_scopes=SCOPES)

#     url = client.oauth2_get_authorize_url()

#     print('Native App Authorization URL: \n{}'.format(url))

#     if not is_remote_session():
#         webbrowser.open(url, new=1)

#     auth_code = get_input('Enter the auth code: ').strip()

#     token_response = client.oauth2_exchange_code_for_tokens(auth_code)

#     # return a set of tokens, organized by resource server name
#     return token_response.by_resource_server


# def main():
#     # start the Native App authentication process
#     tokens = do_native_app_authentication(CLIENT_ID, REDIRECT_URI)

#     transfer_token = tokens['transfer.api.globus.org']['access_token']

#     authorizer = AccessTokenAuthorizer(access_token=transfer_token)
#     transfer = TransferClient(authorizer=authorizer)

#     # print out a directory listing from an endpoint
#     transfer.endpoint_autoactivate(TUTORIAL_ENDPOINT_ID)
#     for entry in transfer.operation_ls(TUTORIAL_ENDPOINT_ID, path='/~/'):
#         print(entry['name'] + ('/' if entry['type'] == 'dir' else ''))

################################################################################



################################################################################

###
# Doing ls and a transfer between spt#buffer and RCC
###

# # a GlobusAuthorizer is an auxiliary object we use to wrap the token. In
# # more advanced scenarios, other types of GlobusAuthorizers give us
# # expressive power
# authorizer = globus_sdk.AccessTokenAuthorizer(TRANSFER_TOKEN)
# tc = globus_sdk.TransferClient(authorizer=authorizer)

# # # high level interface; provides iterators for list responses
# # print("My Endpoints:")
# # for ep in tc.endpoint_search(filter_scope="my-endpoints"):
# #     print("[{}] {}".format(ep["id"], ep["display_name"]))

# # print(config["Globus"])

# # print(tc.get_endpoint(config["Globus"]["destination_endpoints"]["rcc"]))
# # 'destination_endpoints': '{"rcc": "af7bda53-6d04-11e5-ba46-22000b92c6ec", "nersc_hpss": "9cd89cfd-6d04-11e5-ba46-22000b92c6ec"}'

# print(tc.endpoint_autoactivate(
#     config["Destination"]["endpoint"]["rcc"]))
# # for endpoint in config["Globus"]["destination_endpoints"]
# ep1result = tc.endpoint_autoactivate(config["Origin"]["endpoint"])
# ep2result = tc.endpoint_autoactivate(config["Destination"]["endpoint"]["rcc"])

# r = tc.operation_ls(config["Origin"]["endpoint"],
#                     path=config["Origin"]["file_location"])
# print("==== Endpoint_ls for endpoint {} {} ====".format(config["Origin"]["endpoint"], config["Origin"]["file_location"]))
# for item in r:
#     print("{}: {} [{}]".format(item["type"], item["name"], item["size"]))

# r = tc.operation_ls(config["Destination"]["endpoint"]["rcc"],
#                     path=config["Destination"]["file_location"]["rcc"])
# print("==== Endpoint_ls for endpoint {} {} ====".format(config["Destination"]["endpoint"]["rcc"], config["Destination"]["file_location"]["rcc"]))
# for item in r:
#     print("{}: {} [{}]".format(item["type"], item["name"], item["size"]))

# tdata = globus_sdk.TransferData(tc, config["Origin"]["endpoint"],
#                                 config["Destination"]["endpoint"]["rcc"],
#                                 label="rcc")

# ## Recursively transfer source path contents
# tdata.add_item(config["Origin"]["file_location"], config["Destination"]["file_location"]["rcc"], recursive=True)

# # tc.endpoint_autoactivate(config["Origin"]["endpoint"])
# # tc.endpoint_autoactivate(config["Destination"]["file_location"]["rcc"])

# submit_result = tc.submit_transfer(tdata)
# # print("Task ID:", submit_result["task_id"])

################################################################################