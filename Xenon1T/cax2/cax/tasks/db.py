from __future__ import absolute_import, division, print_function
import os
import logging as log
import requests
from json import dumps, loads

from cax import config

# def check_new_run(config):
#     # call DB to check for runs with "transferring" tag
#     pass


# def mark_run_transferred(config, run_date):
#     # 
#     pass

# def check_new_data(config):
#     # 


class DBRESTfulAPI(object):
    def __init__(self, config):
        # Runs DB Query Parameters
        self.api_url = config["API_URL"]
        self.get_params = {
            "username": config["API_user"],
            "api_key": config["API_key"],
            "detector": config["detector"]
        }
        self.next_run = None
        # Runs DB writing parameters
        self.data_set_headers = {
            "content-type": "application/json",
            "Authorization": "ApiKey " + config["API_user"] +
                             ":" + config["API_key"]
        }

        self.logging = logging.getLogger(self.__class__.__name__)

    def get_next_run(self, query):
        ret = None
        if self.next_run == "null":
            return ret
        if self.next_run is None:
            # Prepare query parameters
            params = self.get_params
            if 'detector' in params and params['detector'] == 'all':
                params.pop('detector')
            for key in query.keys():
                params[key] = query[key]
            params['limit'] = 1
            params['offset'] = 0
            ret = requests.get(self.api_url, params=params)
        else:
            ret = requests.get(self.next_run)
        # Keep track of the next run so we can iterate.
        if ret is not None:
            self.next_run = ret['next']
            return ret['doc']
        return ret

    def add_location(self, uuid, parameters):
        # Adds a new data location to the list

        # Parameters must contain certain keys.
        required = ["host", "location", "checksum", "status", "type"]
        if not all(key in parameters for key in required):
            raise NameError("attempt to update location without required keys")

        url = self.api_url + uuid + "/"
        ret = requests.put(url, data=parameters,
                           headers=self.data_set_headers)

    def remove_location(self, uuid, parameters): 
        # Removes a data location from the list
        parameters['status'] = "remove"
        self.add_location(uuid, parameters)
        
    def update_location(self, uuid, remove_parameters, add_parameters):
        # Removes location from the list then adds a new one
        self.remove_location(uuid, remove_parameters)
        self.add_location(uuid, add_parameters)