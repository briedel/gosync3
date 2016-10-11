import ast
import ConfigParser


def parse_config(config_file):
    config = ConfigParser.ConfigParser()
    config.optionxform = str
    config.read(options.config)
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
