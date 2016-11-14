from __future__ import print_function
import ast
import ConfigParser as configparser
import logging as log
import os
import time
import stat
import shutil

try:
    from nexus import GlobusOnlineRestClient
except:
    log.error(("Cannot import Globus Nexus. Trying to "
                   "import Globus SDK Auth Client"))
    try:
        from globus_sdk import AuthClient
    except:
        log.error(("Cannot import Globus Auth Client "
                       "or Globus Nexus. Exiting"))
        raise RuntimeError()


def parse_config(config_file):
    """
    Have configparser open the config file
    and generate a dict mapping sections
    and options in a dict(dict())

    Args:
        config_file: Path to config file

    Returns:
        config_dict: Dict(dict()) of the format
                     config[section_header][variable_name]=
                     variable_value
    """
    config = configparser.ConfigParser()
    config.optionxform = str
    config.read(config_file)
    config_dict = config_options_dict(config)
    return config_dict


def config_options_dict(config):
    """
    Parsing config file

    Args:
        config: Python config parser object

    Returns:
        config_dict: A dict(dict()) with the different sections of the
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


def uniclean(to_clean):
    """
    Cleaning out unicode from Globus output. Unicode gets
    encoded into latin-1. Might need to change this encoding

    Args:
        to_clean: Object to be cleaned of unicode

    Returns:
        Object of same type that has be cleaned
        of unicode
    """
    if isinstance(to_clean, str):
        return to_clean
    if isinstance(to_clean, unicode):
        return to_clean.encode('latin-1', 'replace')
    if isinstance(to_clean, list):
        return [uniclean(x) for x in to_clean]
    if isinstance(to_clean, dict):
        return dict((str(k), uniclean(v))
                    for k, v in to_clean.items())
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

    Args:
        group: Group to filtered
        filters: Filter

    Returns:
        Group without filter
    """
    for f in filters:
        if "osg" in f:
            return group.split('.')[-1]
        elif ("duke" in f or "atlas" in f):
            return group.replace('.', '-')


def recursive_chown(path, uid, gid):
    """
    Walk through directory tree and chown everything

    Args:
        path: Top level dir where to start
        uid: UNIX ID of the user
        gid: UNIX id of the group
    """
    for root, dirs, files in os.walk(path):
        os.chown(root, uid, gid)
        for momo in dirs:
            os.chown(os.path.join(root, momo), uid, gid)
        for momo in files:
            os.chown(os.path.join(root, momo), uid, gid)


def backup_file(filename):
    """
    Backup file by copying it to a location with a timestamp

    Args:
        filename: Filename to backup
    """
    t = time.localtime()
    timestamp = time.strftime('%b-%d-%Y_%H%M', t)
    shutil.copyfile(filename, filename + "_" + timestamp)


def convert_passwd_line(passwd_line):
    """
    Make sure we are writing a string to the
    text file

    Args:
        passwd_line: List, tuple, or string of information in
                     /etc/passwd line

    Returns:
        passwd_line: String that is a /etc/passwd line
    """
    if (isinstance(passwd_line, list) or
       isinstance(passwd_line, tuple)):
        if len(passwd_line) != 7:
            log.error(("List or tuple does not have the right length "
                       "please check what you are trying to write to "
                       "the passwd file."))
            raise RuntimeError()
        print(passwd_line)
        passwd_line = ":".join(passwd_line)
        print(passwd_line)
    elif (not isinstance(passwd_line, str) or
          ":" not in passwd_line):
        log.error("passwd_line does not have expected format")
        raise RuntimeError()
    return passwd_line


def edit_passwd_file(config, passwd_lines, mode):
    """
    Adding to or creating new /etc/passwd-style file

    Args:
        config: Configuration parameters dict()
        passwd_lines: List of lines to be added passwd file
        mode: Either "append" or "overwrite" to append to
              a file or overwrite a file
    """
    if mode == "append":
        mode = "at"
    elif mode == "overwrite":
        mode = "wt"
    else:
        log.error(("Please select 'append' or 'overwrite' "
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
        elif passwd_lines is None:
            return
        else:
            log.error(("Cannot write to password file because "
                       "inputs are a list/tuple of list/tuple,"
                       "list/tuple, or string"))
            raise RuntimeError()


def create_user_dirs(config, member, passwd_line, create_user_storage=True):
    """
    Create user home directory and (optionally) their stash directory

    Args:
        config: Configuration parameters dict()
        member: Globus member
        passwd_lines: List of lines to be added passwd file
        create_user_storage: (optional) create users storage directory
    """
    home_dir = get_home_dir(config, member)
    create_home_dir(home_dir)
    group = member[1]["group_name"]
    top_group = group.split(".")[0] if "project" not in group else "osg"
    if config["debug"]["debug"]:
        user_storage_dir = config["debug"]["dummy_stash"]
    else:
        if top_group not in config["groups"]["storage_dir"].keys():
            log.fatal(("Top group %s has not defined "
                       "user storage directory. Please add."))
            raise RuntimeError()
        user_storage_dir = os.path.join(config["groups"]["storage_dir"][top_group],
                                        "user", "")
    create_user_storage_dir(member, passwd_line,
                            home_dir, top_level_dir=user_storage_dir)
    recursive_chown(home_dir, int(passwd_line[2]), int(passwd_line[3]))


def get_home_dir(config, member):
    """
    Get Home directory path

    Args:
        config: Configuration parameters dict()
        member: Globus member

    Returns:
        home_dir: String of home directory path
    """
    if config["debug"]["debug"]:
        home_dir = os.path.join(config["debug"]["dummy_home"],
                                member[0])
    else:
        home_dir = os.path.join(config["users"]["home_dir"],
                                member[0])
    return home_dir


def create_home_dir(home_dir):
    """
    Create Home directory

    Args:
        home_dir: String of home directory path
    """
    if not os.path.exists(home_dir):
        log.debug("Creating home directory %s", home_dir)
        os.makedirs(home_dir)
        # copy skeleton home dir into home
        for file in os.listdir("/etc/skel/"):
            shutil.copy2(os.path.join("/etc/skel/", file),
                         os.path.join(home_dir, ""))
        os.chmod(home_dir, stat.S_IRWXU)


def create_user_storage_dir(member, passwd_line,
                            home_dir=None,
                            top_level_dir="/stash/user/"):
    """
    Create user storage directory

    Args:
        member: Globus member
        passwd_line: List with user information. Every entry
                     corresponds to position  of the information in
                     the users passwd file.
        home_dir: String of home directory path
        top_level_dir: Top level directory where to put
                       user storage scheme
    """
    storage_dir = os.path.join(top_level_dir, member[0])
    if not os.path.exists(storage_dir):
        log.debug("Creating user storage directory %s")
        os.makedirs(storage_dir)
        os.makedirs(os.path.join(storage_dir, "public"))
    recursive_chown(storage_dir, int(passwd_line[2]), int(passwd_line[3]))
    if home_dir is not None:
        os.symlink(storage_dir, os.path.join(home_dir, "stash"))
        os.symlink(os.path.join(storage_dir, "public"),
                   os.path.join(home_dir, "public"))


def add_ssh_key(config, member):
    """
    Adding ssh key file to users home directory

    Args:
        config: Configuration parameters dict()
        member: Globus Nexus member object
    """
    ssh_dir = os.path.join(get_home_dir(config, member), ".ssh")
    if not os.path.exists(ssh_dir):
        os.makedirs(ssh_dir)
        os.chmod(ssh_dir, stat.S_IRWXU)
    auth_keys_file = os.path.join(ssh_dir, "authorized_keys")
    with open(auth_keys_file, "wt") as f:
        for key in member[1]["user_profile"][1]["ssh_pubkeys"]:
            f.write(key["ssh_key"])
    os.chmod(auth_keys_file, stat.S_IRUSR | stat.S_IWUSR)


def add_email_forwarding(config, member):
    """
    Adding email forwarding file to users home directory

    Args:
        config: Configuration parameters dict()
        member: Globus Nexus member object
    """
    forward_file = os.path.join(get_home_dir(config, member), ".forward")
    with open(forward_file, "wt") as f:
        f.write(str(member[1]["user_profile"][1]["email"]))
    os.chmod(forward_file, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
    os.chown(forward_file, member["user_id"], member["group_id"])
