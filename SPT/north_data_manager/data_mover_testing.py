#!/usr/bin/env python
from __future__ import print_function
import argparse
import globus_sdk
import os
from util import parse_config
from m2 import create_proxy_from_file

parser = argparse.ArgumentParser()
parser.add_argument("--config", help="Config file",
                    dest="config_file", type=str)
args = parser.parse_args()

config = parse_config(args.config_file)


def get_globus_tokens(config):
    """
    Get Globus authenication tokens
    """
    client = globus_sdk.NativeAppAuthClient(
        config["Globus"]["client_id"])
    client.oauth2_start_flow(refresh_tokens=True)
    if os.path.exists("/home/briedel/.spt_transfer"):
        with open("/home/briedel/.spt_transfer", "rt") as f:
            for line in f:
                transfer_refresh_token = line.rstrip("\n")
        return client, None, None, transfer_refresh_token
    else:
        authorize_url = client.oauth2_get_authorize_url()
        print('Please go to this URL and login: {0}'.format(authorize_url))
        # this is to work on Python2 and Python3 -- you can just
        # use raw_input() or input() for your specific version
        get_input = getattr(__builtins__, 'raw_input', input)
        auth_code = get_input(
            'Please enter the code you get after login here: ').strip()
        token_response = client.oauth2_exchange_code_for_tokens(auth_code)

        globus_auth_data = token_response.by_resource_server['auth.globus.org']
        globus_transfer_data = token_response.by_resource_server[
            'transfer.api.globus.org']

        auth_token = globus_auth_data[
            'access_token']
        transfer_token = globus_transfer_data[
            'access_token']
        transfer_refresh_token = globus_transfer_data[
            'refresh_token']
        with open("/home/briedel/.spt_transfer", "wt") as f:
            f.write(transfer_refresh_token)
        return client, auth_token, transfer_token, transfer_refresh_token


def extend_credentials_X509_activate(config, endpoint, tc):
    """"
    Function to generate a X509 proxy and use that to authenticate
    against a Globus Online Endpoint

    Args:
        config: config paramaters as a dict()
        endpoint: the name of the endpoint here that is mapped
                  to its uuid in the config
        tc: Globus SDK transfer client
    """
    # Get the methods of activation for this GO endpoint
    act_req = tc.endpoint_get_activation_requirements(
        config["Destination"]["endpoint"][endpoint])
    # In the possible authentication methods look for
    # the "delegate proxy" type. It should appear twice
    # once with the name "public key" and another with
    # the name "proxy chain"
    for d in act_req["DATA"]:
        if d["type"] != "delegate_proxy":
            continue
        if d["name"] == "public_key":
            key_blob = d
        if d["name"] == "proxy_chain":
            chain_blob = d
    # Take the "value" of the "public key" 
    # delegate proxy and your special PEM
    # file to generate a new proxy. This is basically
    # grid-proxy-init specific to the site
    # `create_proxy_from_file` comes from the m2.py
    new_proxy = create_proxy_from_file(
        config["globus"]["pem_file"],
        key_blob["value"],
        lifetime_hours=config["globus"]["proxy_lifetime"])
    # Replace the "proxy chain" "value" wth the new proxy
    chain_blob["value"] = new_proxy
    # Activate the endpoint by passing it 
    # a new "activation_requirements" data type
    # that contains the endpoints "public key"
    # and "proxy chain"
    epresult = tc.endpoint_activate(
        config["Destination"]["endpoint"][endpoint],
        {"DATA_TYPE": "activation_requirements",
         "DATA": [key_blob, chain_blob]})
    return epresult


(client, auth_token,
 transfer_token, transfer_refresh_token) = get_globus_tokens(config)

if transfer_token is not None:
    authorizer = globus_sdk.AccessTokenAuthorizer(transfer_token)
else:
    authorizer = globus_sdk.RefreshTokenAuthorizer(
        transfer_refresh_token, client)
# authorizer = globus_sdk.AccessTokenAuthorizer(transfer_token)
tc = globus_sdk.TransferClient(authorizer=authorizer)

for endpoint in config["Destination"]["endpoint"].keys():
    if endpoint == "nersc":
        ep2result = extend_credentials_X509_activate(config, endpoint)
    else:
        ep2result = tc.endpoint_autoactivate(config["Destination"][
            "endpoint"][endpoint])
    tdata = globus_sdk.TransferData(tc,
                                    config["Origin"]["endpoint"],
                                    config["Destination"][
                                        "endpoint"][endpoint],
                                    verify_checksum=True,
                                    sync_level="checksum")
    for loc in config["Origin"]["file_location"]:
        # Recursively transfer source path contents
        tdata.add_item(loc,
                       os.path.join(config["Destination"][
                                    "file_location"][endpoint],
                                    os.path.basename(loc)),
                       recursive=True)

    transfer_result = tc.submit_transfer(tdata)
