from __future__ import absolute_import, division, print_function
import os
import glob
import logging as log

from rucio.client import Client
from rucio.rse import rsemanager as rsemgr
from rucio.common.exception import (DataIdentifierAlreadyExists,
                                    Duplicate, FileAlreadyExists,
                                    AccessDenied, ResourceTemporaryUnavailable,
                                    DataIdentifierNotFound, InvalidObject,
                                    RSENotFound, InvalidRSEExpression,
                                    DuplicateContent, RSEProtocolNotSupported,
                                    RuleNotFound, CannotAuthenticate,
                                    MissingDependency, UnsupportedOperation,
                                    FileConsistencyMismatch, RucioException)
from cax.util import *
from cax.db import check_new_run


class Transfer(object):
    """
    Base class for the transfer classes
    Mostly to provide future expansion for common functions
    """
    def __init__(self, config):
        """
        Initialize

        Args:
            config: cluster config dict for cluster
        """
        self.config = config

    def find_files(self, direc, file_ids):
        files = []
        for ids in file_ids:
            files += glob.glob(os.path.join(direc, ids))
        return files

    def upload(self):
        raise NotImplementedError()

    def download(self):
        raise NotImplementedError()


class TransferRucio(Transfer):
    """
    Class for Rucio transfers
    """
    def __init__(self, config, rucio_config):
        Transfer.__init__(self, config)
        self.rucio_config = rucio_config
        self.client = self.get_rucio_client()

    def get_rucio_client(self):
        """
        Returns a new rucio client object.

        Args:
            rucio_config: Dict() generated from json rucio.json

        Returns:
            client: rucio client object
        """
        try:
            client = Client(rucio_host=self.rucio_config["host"],
                            auth_host=self.rucio_config["auth_host"],
                            account=self.rucio_config["account"],
                            auth_type=self.rucio_config["account"],
                            creds=self.rucio_config["credentials"],
                            ca_cert=self.rucio_config["ca_certificate"],
                            timeout=self.rucio_config["timeout"],
                            user_agent=self.rucio_config["user_agent"])
        except CannotAuthenticate, error:
            logger.error(error)
            if not self.rucio_config["auth_strategy"]:
                if 'RUCIO_AUTH_TYPE' in os.environ:
                    auth_type = os.environ['RUCIO_AUTH_TYPE']
                else:
                    try:
                        auth_type = config_get('client', 'auth_type')
                    except (NoOptionError, NoSectionError):
                        log.error('Cannot get AUTH_TYPE')
                        raise RuntimeError()
            if auth_type == 'x509_proxy':
                log.error(('Please verify that your X509 proxy '
                           'is still valid and renew it if needed.'))
                raise RuntimeError()
        return client

    def upload(self, direc, file_ids,
               scope, rse, dataset_name=None):
        rse_settings = rsemgr.get_rse_info(rse)
        if rse_settings['availability_write'] != 1:
            log.FATAL("Cannot write to RSE. Please check settings")
            raise RuntimeError()
        files = find_files(direc, file_ids)
        if files:
            log.FATAL("Cannot find any files.")
            raise RuntimeError()
        files_to_list = []
        list_files = []
        revert_dict = {}
        lfns = {}
        # Gathering all the information needed to add files to the
        # catalog. Make sure we can add files to the catalog
        for name in files:
            try:
                size = os.stat(name).st_size
                checksum = adler32(name)
                log.debug(('Extracting filesize (%s) and '
                           'checksum (%s) for file %s:%s'),
                          size, checksum, scope, os.path.basename(name))
                files_to_list.append({'scope': scope,
                                     'name': os.path.basename(name)})
                list_files.append({'scope': scope,
                                   'name': os.path.basename(name),
                                   'bytes': size,
                                   'adler32': checksum,
                                   'state': 'C',
                                   'meta': {'guid': generate_uuid()}})
                if not os.path.dirname(name) in lfns:
                    lfns[os.path.dirname(name)] = []
                lfns[os.path.dirname(name)].append({'name': os.path.basename(name),
                                                    'scope': scope,
                                                    'adler32': checksum,
                                                    'filesize': size})
                revert_dict[fscope,
                            os.path.basename(name)] = os.path.dirname(name)
            except OSError, error:
                log.error(error)
                log.error("No operation will be performed. Exiting!")
                raise RuntimeError()
        if dataset_name is not None:
            self.client.add_dataset(scope=scope,
                                    name=dataset_name,
                                    rules=[{'account': self.client.account,
                                            'copies': 1,
                                            'rse_expression': rse,
                                            'grouping': 'DATASET'
                                           }])
        # Adding files to the catalog
        for f in list_files:
            # If the did already exist in the catalog,
            # only should be upload if the checksum is the same
            try:
                meta = self.client.get_metadata(f['scope'], f['name'])
                did = {'scope': f['scope'], 'name': f['name']}
                replicastate = [rep
                                for rep in self.client.list_replicas([did],
                                                                      all_states=True)]
                if rse not in replicastate[0]['rses']:
                    self.client.add_replicas(files=[f], rse=args.rse)
                if rsemgr.exists(rse_settings=rse_settings,
                                 files={'name': f['name'],
                                        'scope': f['scope']}):
                    log.warning(('File %s:%s already exists on RSE. '
                                 'Will not try to reupload'),
                                f['scope'],
                                f['name'])
                else:
                    if meta['adler32'] == f['adler32']:
                        log.info(('Local files and file %s:%s '
                                  'recorded in Rucio have the '
                                  'same checksum. Will try the upload'),
                                 f['scope'],
                                 f['name'])
                        directory = revert_dict[f['scope'], f['name']]
                        rsemgr.upload(rse_settings=rse_settings,
                                      lfns=[{'name': f['name'],
                                             'scope': f['scope'],
                                             'adler32': f['adler32'],
                                             'filesize': f['bytes']}],
                                      source_dir=directory)
                        logger.info(('File %s:%s successfully '
                                     'uploaded on the storage'),
                                    f['scope'],
                                    f['name'])
                    else:
                        raise DataIdentifierAlreadyExists
            except NotImplementedError, error:
                for proto in rse_settings['protocols']:
                    if proto['domains']['wan']['read'] == 1:
                        prot = proto['scheme']
                log.error(('Protocol %s for RSE {1} '
                           'not supported!'),
                          prot,
                          args.rse)
                raise RuntimeError()
            except DataIdentifierNotFound:
                try:
                    directory = revert_dict[f['scope'], f['name']]
                    rsemgr.upload(rse_settings=rse_settings,
                                  lfns=[{'name': f['name'],
                                         'scope': f['scope'],
                                         'adler32': f['adler32'],
                                         'filesize': f['bytes']}],
                                  source_dir=directory)
                    logger.info(('File %s:%s successfully uploaded '
                                 'on the storage'),
                                f['scope'],
                                f['name'])
                except (Duplicate, FileAlreadyExists), error:
                    logger.warning(error)
                    raise RuntimeError()
                except ResourceTemporaryUnavailable, error:
                    logger.error(error)
                    raise RuntimeError()
            except DataIdentifierAlreadyExists, error:
                logger.debug(error)
                logger.error(("Some of the files already exist "
                              "in the catalog. No one will be added."))
            if dataset_name is not None:
                try:
                    self.client.add_files_to_dataset(scope=scope,
                                                     name=dataset_name,
                                                     files=[f])
                except Exception, error:
                    log.error('Failed to attach file %s to the dataset', f)
                    log.error(error)
                    log.error("Continuing with the next one")
        replicas = []
        replica_dictionary = {}
        for chunk_files_to_list in chunks(files_to_list, 50):
            for rep in self.client.list_replicas(chunk_files_to_list):
                replica_dictionary[rep['scope'],
                                   rep['name']] = rep['rses'].keys()
        for file in list_files:
            if (file['scope'], file['name']) not in replica_dictionary:
                file['state'] = 'A'
                replicas.append(file)
            elif rse not in replica_dictionary[file['scope'],
                                               file['name']]:
                file['state'] = 'A'
                replicas.append(file)
        if replicas != []:
            log.info('Will update the file replicas states')
            for chunk_replicas in chunks(replicas, 20):
                try:
                    self.client.update_replicas_states(rse=rse,
                                                       files=chunk_replicas)
                except AccessDenied, error:
                    logger.error(error)
                    raise RuntimeError()
            log.info('File replicas states successfully updated')

    def create_scope(self, scope):
        """
        Add scope.

        """
        try:
            self.client.add_scope(scope=scope)
            log.info('Added scope %s to account %s',
                     scope,
                     self.client.account)
        except Exception, error:
            log.error(('Could not add '
                      'scope %s to account %s'),
                      scope,
                      self.client.account)
            log.error(error)
            raise RuntimeError()

    def create_dataset(self, scope, name):
        """
        Add a dataset identifier.


        """
        try:
            self.client.add_dataset(scope=scope,
                                    name=name,
                                    statuses={'monotonic': True})
            log.info('Added dataset %s:%s', scope, name)
        except Exception, error:
            log.fatal('Could not create dataset %s:%s', scope, name)
            log.error(error)
            raise RuntimeError()

    def create_container(self, scope, name):
        """
        Add a container identifier.

        """
        try:
            self.client.add_container(scope=scope,
                                      name=name,
                                      statuses={'monotonic': True})
            log.info('Created container %s:%s', scope, name)
        except Exception, error:
            log.fatal('Could not create dataset %s:%s', scope, name)
            log.error(error)
            raise RuntimeError()

    def attach_dids(self, scope, attach_to, attach):
        """
        Attach a data identifier.
        """
        try:
            log.debug("Attaching to %s:%s",
                      scope, attach_to)
            if isinstance(attach, list):
                dids = [{'scope': scope, 'name': name}
                        for name in attach]
            elif isinstance(attach, str):
                dids = [{'scope': scope, 'name': attach}]
            else:
                log.fatal("")
                raise RuntimeError()
            self.client.attach_dids(scope=scope,
                                    name=attach_to,
                                    dids=dids)
            log.info('DIDs successfully attached to %s:%s', scope, name)
        except Exception, error:
            log.fatal('Could not create container %s:%s', scope, name)
            log.error(error)
            raise RuntimeError()

    def get_dids(self, scope, did_type=None):
        if did_type is None:
            did_type = "all"
        log.debug("Getting DID names for scope %s and type %s",
                  scope, did_type)
        dids = [did["name"]
                for did in self.client.list_dids(scope,
                                                 filters=filters,
                                                 type=did_type,
                                                 long=True)]
        return dids

    def upload_raw_data(self):
        # Checking for new run
        run_date = check_new_run(config)
        rucio_client = self.get_rucio_client(rucio_config)
        if run_date is not None:
            # Guessing scope name, create if not present
            scopes = self.client.list_scopes_for_account(self.client.account)
            scope = self.rucio_config["naming_scheme"]["scope"] %\
                config["science_run_number"]
            log.debug("Expected scope is %s", scope)
            if scope not in scopes:
                create_scope(scope)
            # Guessing container name, create if not present
            container = self.rucio_config["naming_scheme"]["container"] %\
                (config["science_run_number"], "raw")
            rucio_containers = get_dids(scope, did_type="container")
            log.debug("Expected container is %s", rucio_containers)
            if container not in rucio_containers:
                create_container(scope, containers)
            # Guessing container name
            dataset = self.rucio_config["naming_scheme"]["tpc"] %\
                (run_date, "raw")
            log.debug("Expected dataset name is %s", rucio_containers)
            # Uploading data to an RSE. If more than one RSE given,
            # rather than uploading the data again, add a replication rule.
            for i, rse in enumerate(config["destination_RSEs"]):
                if i == 0:
                    self.rucio_upload(config["input_dir"],
                                      config["input_file_patterns"], scope,
                                      rse, dataset_name=dataset)
                else:
                    try:
                        rule_ids = self.client.add_replication_rule(
                            dids=[{'scope': scope, 'name': dataset}],
                            copies=1,
                            rse_expression=rse)
                        for rule_id in rule_ids:
                            log.info(("New replication rule "
                                      "added for %s:%s to "
                                      "RSE %s with rule %s"),
                                     scope, dataset, rse, rule_id)
                    except:
                        log.fatal(("Could not add replication rule for "
                                   "dataset %s:%s to RSE %s"),
                                  scope, dataset, rse)
                        log.error(error)
                        raise RuntimeError()
        else:
            log.info("No new run. Exiting.")
            sys.exit()
        # Mark run as transferred
        mark_run_transferred(config, run_date)


class TransferSCP(Transfer):
    """
    Class for SCP transfers
    """
    def __init__(self, config):
        Transfer.__init__(self, config)
        self.rucio_config = rucio_config

    def download_raw_data(self):
        raise NotImplementedError()


# def add_upload_files(config, rucio_config, mode=None):
#     rucio_client = get_rucio_client(rucio_config)
#     if mode is None:
#         log.FATAl(("No mode specified for "
#                    "uploading data to rucio"))
#         raise RuntimeError()
#     elif mode == "raw":
#         upload_raw_data(config, rucio_client)
#     elif mode == "processed":
#         upload_processed_data(config, rucio_config)
#     else:
#         log.FATAl("Mode %s is not supported by add_upload_files()",
#                   mode)
#         raise NotImplementedError()

