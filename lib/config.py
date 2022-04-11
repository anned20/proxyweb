from voluptuous.schema_builder import ALLOW_EXTRA, Extra, Required
from voluptuous.validators import Any, Coerce
import yaml

from models import Config
from voluptuous import Schema


global_config_schema = Schema({
    "hide_tables": [str],
    Required("default_server"): str,
    Required("read_only"): bool,
})

server_config_schema = Schema({
    Extra: {
        Required("dsn"): {
            Required("host"): str,
            Required("port"): Coerce(int),
            Required("user"): str,
            Required("passwd"): str,
            Required("db"): str,
            "read_only": bool,
            "hide_tables": [str],
        }
    },
})

misc_config_schema = Schema({
    Extra: [
        {
            Required("title"): str,
            Required("info"): str,
            Required("sql"): str,
            "variables": {
                Extra: {
                    Required("type"): Any("string", "integer", "float", "boolean"),
                    Required("label"): str,
                    "default": Any(str, int, float, bool),
                }
            }
        }
    ]
})

flask_config_schema = Schema({
    Required("SECRET_KEY"): str,
}, extra=ALLOW_EXTRA)

config_schema = Schema({
    Required("global"): global_config_schema,
    Required("servers"): server_config_schema,
    Required("misc"): misc_config_schema,
    Required("flask"): flask_config_schema,
})


class InvalidConfig(Exception):
    pass


def parse_config(config: str) -> Config:
    """
    Parse a config string and return a dictionary of the values.
    """
    try:
        cfg = yaml.safe_load(config)

        cfg = config_schema(cfg)

        cfg = Config(cfg)

        return cfg
    except Exception as e:
        raise InvalidConfig(f"Error parsing config: {e}")


def parse_config_file(file: str) -> Config:
    """
    Parse a config file and return a dictionary of the values.
    """
    with open(file, "r") as yml:
        return parse_config(yml.read())
