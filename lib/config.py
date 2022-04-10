import logging
import yaml

from models import Config


class InvalidConfig(Exception):
    pass


def parse_config_file(file: str) -> Config:
    """
    Parse a config file and return a dictionary of the values.
    """
    logging.debug("Using file: %s" % (file))

    try:
        with open(file, "r") as yml:
            cfg = yaml.safe_load(yml)

        cfg = Config(cfg)

        return cfg
    except Exception as e:
        raise InvalidConfig(f"Error parsing config file '{file}': {e}")
