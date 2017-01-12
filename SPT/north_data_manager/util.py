from __future__ import print_function
import sys
assert (sys.version_info >= (2, 7) or
        sys.version_info.major >= 3), "Python version 2.7 or 3+ needed"
import ast
try:
    import ConfigParser as configparser
except:
    import configparser



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
            print(val)
            try:
                val = ast.literal_eval(val)
            except Exception:
                pass
            config_dict[section][option] = val
    return config_dict
