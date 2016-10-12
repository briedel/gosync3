import ast
import ConfigParser
import logging

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
    client = GlobusOnlineRestClient(config=nexus_config)
    return client


def get_groups(group_cache):
    pass


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
