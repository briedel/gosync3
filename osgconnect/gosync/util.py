from __future__ import print_function
import ast
import ConfigParser
import logging
import os

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
    config = ConfigParser.ConfigParser()
    config.optionxform = str
    config.read(config_file)
    config_dict = config_options_dict(config)
    return config_dict


def config_options_dict(config):
    """
    Parsing config file
    Args:
        config: Pythong config parser object
    Returns:
        A dict with the different sections of the config file
        and the literal values of the configuraton objects
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
    nexus_config = {"server": config['globus']['server'],
                    "client": "connect",
                    "client_secret": config['secrets']['connect']}
    print(nexus_config)
    client = GlobusOnlineRestClient(config=nexus_config)
    return client


def uniclean(to_clean):
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
    for f in filters:
        if "osg" in f:
            return group.split('.')[-1]
        elif ("duke" in f or "atlas" in f):
            return group.replace('.', '-')


def get_groups_globus(roles):
    return client.get_group_list(my_roles=[roles])[1]


def filter_groups(self, groups, group_names):
    filtered_groups = [g for g in groups if g['name'] in group_names]
    if isinstance(group_names, list):
        return filtered_groups
    elif isinstance(group_names, str):
        return filtered_groups[0]


def get_groupid(self, groups, name):
    return filter_groups(name)['id']


def recursive_chown(path, uid, gid):
    for root, dirs, files in os.walk(path):
        for momo in dirs:
            os.chown(os.path.join(root, momo), uid, gid)
        for momo in files:
            os.chown(os.path.join(root, momo), uid, gid)


def edit_passwd_file(passwd_lines, mode):
    if mode == "append":
        mode = "at"
    elif mode == "overwrite":
        mode = "wt"
    else:
        logging.error(("Please select 'append' or 'overwrite' "
                       "as modes for the passwd file"))
        raise RuntimeError()
    # where to get filename from?
    with open(passwd_filename, mode) as f:
        if isinstance(passwd_lines, list):
            for passwd_line in passwd_lines:
                f.write(passwd_line)
        elif isinstance(passwd_lines, str):
            f.write(passwd_lines)


def create_user_dirs(passwd_line):
    home_dir = passwd_line[-2]
    if not os.path.exists(home_dir):
        os.makedirs(home_dir)
        # copy skeleton home dir into dir
    os.fchmod(home_dir, 2700)
    stash_dir = os.path.join("/stash/user/", passwd_line[0])
    if not os.path.exists(stash_dir):
        os.makedirs(stash_dir)
        os.makedirs(os.path.join(stash_dir, "public"))
    recursive_chown(stash_dir, int(passwd_line[2]), int(passwd_line[3]))
    os.symlink(stash_dir, os.path.join(home_dir, "stash"))
    os.symlink(os.path.join(stash_dir, "public"),
               os.path.join(home_dir, "public"))
    recursive_chown(home_dir, int(passwd_line[2]), int(passwd_line[3]))


def add_ssh_key(member, passwd_line):
    ssh_dir = os.path.join(passwd_line[-2], ".ssh")
    if not os.path.exists(ssh_dir):
        os.makedirs(ssh_dir)
    os.fchmod(ssh_dir, 0700)
    auth_keys_file = os.path.join(ssh_dir, "authorized_keys")
    with open(auth_keys_file, "wt") as f:
        for key in member["ssh"]:
            f.write(key)
    os.fchmod(ssh_dir, 0600)


def add_email_forwarding(member, passwd_line):
    forward_file = os.path.join(passwd_line[-2], ".forward")
    with open(forward_file, "wt") as f:
        f.write(str(member["email"]))
    os.fchmod(forward_file, 644)
    os.chown(forward_file, int(passwd_line[2]), int(passwd_line[3]))
