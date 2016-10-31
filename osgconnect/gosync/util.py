from __future__ import print_function
import ast
import ConfigParser as configparser
import logging
import os
import time
import socket
import shutil

try:
    from nexus import GlobusOnlineRestClient
except:
    logging.error(("Cannot import Globus Nexus. Trying to "
                   "import Globus SDK Auth Client"))
    try:
        from globus_sdk import AuthClient
    except:
        logging.error(("Cannot import Globus Auth Client "
                       "or Globus Nexus. Exiting"))
        raise RuntimeError()


def parse_config(config_file):
    """
    Have configparser open the config file
    and generate a dict mapping sections
    and options in a dict(dict())
    """
    config = configparser.ConfigParser()
    config.optionxform = str
    config.read(config_file)
    config_dict = config_options_dict(config)
    return config_dict


def config_options_dict(config):
    """
    Parsing config file
    :param config: Python config parser object
    :returns: A dict(dict()) with the different sections of the
              config file and the literal values of the
              configuraton objects
    """
    config_dict = {}
    for section in config.sections():
        config_dict[section] = {}
        for option in config.options(section):
            val = config.get(section, option)
            try:
                val = ast.literal_eval(val)
            except Exception:
                pass
            config_dict[section][option] = val
    return config_dict


def get_globus_client(config):
    """
    Get Globus Nexus RESTful client

    :param config: (optional requires options) Configuration parameters dict()
    :return: Globus Nexus RESTful client
    """
    nexus_config = {"server": config['globus']['server'],
                    "client": config['globus']['client_user'],
                    "client_secret": config['secrets']['connect']}
    client = GlobusOnlineRestClient(config=nexus_config)
    return client


def uniclean(to_clean):
    """
    Cleaning out unicode from Globus output. Unicode gets
    encoded into latin-1. Might need to change this encoding

    :param to_clean: Object to be cleaned of unicode
    :return: Object of same type that has be cleaned
             of unicode
    """
    if isinstance(to_clean, str):
        return to_clean
    if isinstance(to_clean, unicode):
        return to_clean.encode('latin-1', 'replace')
    if isinstance(to_clean, list):
        return [uniclean(x) for x in to_clean]
    if isinstance(to_clean, dict):
        new = {}
        for k, v in to_clean.items():
            new[str(k)] = uniclean(v)
        return new
    return None


def callback_optparse(option, opt_str, value, parser):
    """
    Allow OptionParser in Python2.6 to have variable length
    lists of arguments to an option. Equivalent in Python2.7
    is nargs="+"
    """
    args = []
    for arg in parser.rargs:
        if arg[0] != "-":
            args.append(arg)
        else:
            del parser.rargs[:len(args)]
            break
    if getattr(parser.values, option.dest):
        args.extend(getattr(parser.values, option.dest))
    setattr(parser.values, option.dest, args)


def strip_filters(group, filters):
    """
    Stripping Globus specific prefixes from
    Globus group names

    :param group: Group to filtered
    :param filters: Filter
    :return: Group without filter
    """
    for f in filters:
        if "osg" in f:
            return group.split('.')[-1]
        elif ("duke" in f or "atlas" in f):
            return group.replace('.', '-')


def get_groups_globus(client, roles):
    """
    Get list of Globus groups

    :param client: Globus Nexus Client
    :param roles: Globus Nexus roles
    :return: List of all groups in Globus Nexus groups
             that are associated with a role
    """
    if isinstance(roles, str):
        return client.get_group_list(my_roles=[roles])[1]
    if isinstance(roles, list):
        return client.get_group_list(my_roles=roles)[1]


def get_groups(config, group_cache, dump_groups=False,
               remove_unicode=False):
    if remove_unicode:
        group_cache = uniclean(group_cache)
    groups = [g for g in group_cache
              if (g['name'].startswith(tuple(config["groups"]["filters"])) or
                  (g['name'] == config["globus"]["root_group"] and
                   not dump_groups))]
    groups.sort(key=lambda k: k['name'])
    return groups


def filter_groups(groups, group_names):
    """
    Return group(s) we are interested in

    :param groups: List of Globus Nexus groups
    :param group_names: Group(s) we are interested in
    :return: List of or individual group(s)
    """
    if isinstance(group_names, str):
        group_names = [group_names]
    filtered_groups = [g for g in groups if g['name'] in group_names]
    if isinstance(group_names, list):
        return filtered_groups
    elif isinstance(group_names, str):
        return filtered_groups[0]


def get_groupid(groups, names=None):
    """
    Get the Globus Nexus ID for the group

    :param groups: List of Globus Nexus groups
    :param names: Group(s) we are interested in
    :return: List of or individual group(s) ids
    """
    if names is not None:
        groups = filter_groups(groups, names)
    if isinstance(groups, list):
        ids = {g['id']: g for g in groups}
        return ids
    else:
        return [groups['id']]


# def get_groupids(globus_groups, groups, names):
#     # groups_cache = get_groups_globus(client,
#     #                                  ['admin', 'manager'])
#     # grps = get_groups(options, groups_cache)
#     if isinstance(groups, str):
#         groups = [groups]
#     globus_groups = [g for g in globus_groups if g['name'] in groups]
#     return get_groupid_from_groups(globus_groups, names)


def get_globus_group_members(options, config, client,
                             globus_groups=None, groups=None,
                             dump_users_groups=False):
    """
    Getting all the active members of the group from globus nexus

    :param config: Configuration parameters dict()
    :param client: Globus Nexus RESTful client
    :return: List of "active" members
    """
    members = []
    if groups is None and globus_groups is None:
        # Get the group id of the root group
        group_cache = get_groups_globus(client, ['admin', 'manager'])
        globus_groups = get_groups(config, group_cache)
        groups = config["globus"]["root_group"]
    group_ids = get_groupid(globus_groups, groups)
    for group_id, group in group_ids.items():
        try:
            headers, response = client.get_group_members(group_id)
        except socket.timeout:
            logging.error("Globus Nexus Server response timed out. Skipping.")
            time.sleep(5)
            continue
        if dump_users_groups:
            members += [(member, group['name'], group_id)
                        for member in response['members']
                        if member and member['status'] == 'active']
        else:
            members += [member for member in response['members']
                        if member and member['status'] == 'active']
    # members.sort(key=lambda m: m['name'])
    return members


def get_usernames(members):
    if instannce(members[0], tuple):
        return [member[0]["username"] for member in members]
    return [member["username"] for member in members]


def recursive_chown(path, uid, gid):
    """
    Walk through directory tree and chown everything

    :param path: Top level dir where to start
    :param uid: UNIX ID of the user
    :param gid: UNIX id of the group
    """
    for root, dirs, files in os.walk(path):
        for momo in dirs:
            os.chown(os.path.join(root, momo), uid, gid)
        for momo in files:
            os.chown(os.path.join(root, momo), uid, gid)


def backup_file(filename):
    """
    Backup file by copying it to a location with a timestamp

    :param filename: Filename to backup
    """
    t = time.localtime()
    timestamp = time.strftime('%b-%d-%Y_%H%M', t)
    shutil.copyfile(filename, filename + "_" + timestamp)


def convert_passwd_line(passwd_line):
    """
    Make sure we are writing a string to the
    text file

    :param passwd_line: List, tuple, or string
    :return:
    """
    print(len(passwd_line))
    print(passwd_line)
    if (isinstance(passwd_line, list) or
       isinstance(passwd_line, tuple)):
        if len(passwd_line) != 7:
            logging.error("List or tuple does not have the right length "
                          "please check what you are trying to write to "
                          "the passwd file. ")
            raise RuntimeError()
        print(passwd_line)
        passwd_line = ":".join(passwd_line)
        print(passwd_line)
    elif (not isinstance(passwd_line, str) or
          ":" not in passwd_line):
        logging.error("passwd_line does not have expected format")
        raise RuntimeError()
    print(type(passwd_line))
    return passwd_line


def edit_passwd_file(config, passwd_lines, mode):
    """
    Adding to or creating new /etc/passwd-style file

    :param passwd_lines: List of lines to be added passwd file
    :param config: Configuration parameters dict()
    :param mode: Either "append" or "overwrite" to append to
                 a file or overwrite a file
    """
    if mode == "append":
        mode = "at"
    elif mode == "overwrite":
        mode = "wt"
    else:
        logging.error(("Please select 'append' or 'overwrite' "
                       "as modes for the passwd file"))
        raise RuntimeError()
    if os.path.exists(config['users']['passwd_file']):
        backup_file(config['users']['passwd_file'])
    with open(config['users']['passwd_file'], mode) as f:
        if (isinstance(passwd_lines[0], list) or
           isinstance(passwd_lines[0], tuple)):
            for passwd_line in passwd_lines:
                passwd_line = convert_passwd_line(passwd_line)
                f.write(passwd_line + "\n")
        elif (isinstance(passwd_lines, list) or
              isinstance(passwd_lines, tuple)):
            passwd_line = convert_passwd_line(passwd_lines)
            f.write(passwd_line + "\n")
        elif isinstance(passwd_lines, str):
            passwd_line = convert_passwd_line(passwd_lines)
            f.write(passwd_line + "\n")
        else:
            logging.error("Cannot write to password file because "
                          "inputs are a list/tuple of list/tuple,"
                          "list/tuple, or string")
            raise RuntimeError()


def create_user_dirs(passwd_line, create_stash_like=True):
    """
    Create user home directory and (optionally) their stash directory

    :param passwd_lines: List of lines to be added passwd file
    :param create_stash: (optional) create users stash directory
    """
    home_dir = passwd_line[-2]
    if not os.path.exists(home_dir):
        os.makedirs(home_dir)
        # copy skeleton home dir into dir
    os.fchmod(home_dir, 2700)
    # if create_stash_like and #osg or duke:
    #     create_stash_dir(passwd_line)
    # elif create_stash_like and # atlas:

    # elif create_stash_like and #spt:

    recursive_chown(home_dir, int(passwd_line[2]), int(passwd_line[3]))


def create_stash_dir(passwd_line):
    home_dir = passwd_line[-2]
    stash_dir = os.path.join("/stash/user/", passwd_line[0])
    if not os.path.exists(stash_dir):
        os.makedirs(stash_dir)
        os.makedirs(os.path.join(stash_dir, "public"))
    recursive_chown(stash_dir, int(passwd_line[2]), int(passwd_line[3]))
    os.symlink(stash_dir, os.path.join(home_dir, "stash"))
    os.symlink(os.path.join(stash_dir, "public"),
               os.path.join(home_dir, "public"))


def add_ssh_key(member, passwd_line):
    """
    Adding ssh key file to users home directory

    :param member: Globus Nexus member object
    :param passwd_line: passwd_line providing home dir
    """
    ssh_dir = os.path.join(passwd_line[-2], ".ssh")
    if not os.path.exists(ssh_dir):
        os.makedirs(ssh_dir)
    os.fchmod(ssh_dir, 0700)
    auth_keys_file = os.path.join(ssh_dir, "authorized_keys")
    with open(auth_keys_file, "wt") as f:
        for key in member["ssh"]:
            f.write(key)
    os.fchmod(auth_keys_file, 0600)


def add_email_forwarding(member, passwd_line):
    """
    Adding email forwarding file to users home directory

    :param member: Globus Nexus member object
    :param passwd_line: passwd_line providing home dir
    """
    forward_file = os.path.join(passwd_line[-2], ".forward")
    with open(forward_file, "wt") as f:
        f.write(str(member["email"]))
    os.fchmod(forward_file, 644)
    os.chown(forward_file, int(passwd_line[2]), int(passwd_line[3]))
