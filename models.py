from typing import Dict, List, Literal, Mapping, Optional, Union
import json_fix


__all__ = ["json_fix", ]


class AttrDict(Mapping):
    def __init__(self, init=None):
        if init is not None:
            self.__dict__.update(init)

    def __getitem__(self, key):
        return self.__dict__[key]

    def __setitem__(self, key, value):
        self.__dict__[key] = value

    def __delitem__(self, key):
        del self.__dict__[key]

    def __contains__(self, key):
        return key in self.__dict__

    def __len__(self):
        return len(self.__dict__)

    def __repr__(self):
        return repr(self.__dict__)

    def __iter__(self):
        return iter(self.__dict__)

    def __json__(self):
        return self.__dict__

    def items(self):
        return self.__dict__.items()


class GlobalConfig(AttrDict):
    hide_tables: bool
    default_server: str
    read_only: bool

    def __init__(self, config):
        super().__init__({
            "hide_tables": config["hide_tables"],
            "default_server": config["default_server"],
            "read_only": config["read_only"],
        })


class ServerDsn(AttrDict):
    host: str
    port: int
    user: str
    passwd: str
    db: str

    def __init__(self, dsn):
        super().__init__({
            "host": dsn["host"],
            "port": int(dsn["port"]),
            "user": dsn["user"],
            "passwd": dsn["passwd"],
            "db": dsn["db"],
        })


class Server(AttrDict):
    name: str
    dsn: ServerDsn
    read_only: Optional[bool]
    hide_tables: Optional[List[str]]

    def __init__(self, name, server):
        super().__init__({
            "name": name,
            "dsn": ServerDsn(server["dsn"]),
            "read_only": server["read_only"] if "read_only" in server else None,
            "hide_tables": server["hide_tables"] if "hide_tables" in server else None,
        })


class ServersConfig(AttrDict):
    def __init__(self, config):
        super().__init__({
            name: Server(name, server) for name, server in config.items()
        })


class MiscQueryVariable(AttrDict):
    type: Literal["string", "integer", "float", "boolean"]
    label: str
    default: Optional[Union[str, int, float, bool]]

    def __init__(self, variable):
        super().__init__({
            "type": variable["type"],
            "label": variable["label"],
            "default": variable["default"] if "default" in variable else None,
        })


class MiscQuery(AttrDict):
    title: str
    info: Optional[str]
    sql: str
    variables: Dict[str, MiscQueryVariable]

    def __init__(self, query):
        variables = {}

        if "variables" in query:
            for name, variable in query["variables"].items():
                variables[name] = MiscQueryVariable(variable)

        super().__init__({
            "title": query["title"],
            "info": query["info"] or None,
            "sql": query["sql"],
            "variables": variables,
        })


class MiscCategory(AttrDict):
    name: str
    queries: List[MiscQuery]

    def __init__(self, name, category):
        super().__init__({
            "name": name,
            "queries": [MiscQuery(query) for query in category],
        })


class MiscConfig(AttrDict):
    categories: Dict[str, MiscCategory]

    def __init__(self, config):
        categories = [MiscCategory(name, category) for name, category in config.items()]

        # Sort categories by name
        categories.sort(key=lambda c: c.name)

        super().__init__({
            "categories": {c.name: c for c in categories},
        })


class FlaskConfig(AttrDict):
    SECRET_KEY: str
    SEND_FILE_MAX_AGE_DEFAULT: int
    TEMPLATES_AUTO_RELOAD: bool

    def __init__(self, config):
        super().__init__({
            "SECRET_KEY": config["SECRET_KEY"],
            "SEND_FILE_MAX_AGE_DEFAULT": config["SEND_FILE_MAX_AGE_DEFAULT"],
            "TEMPLATES_AUTO_RELOAD": config["TEMPLATES_AUTO_RELOAD"],
        })


class Config(AttrDict):
    glob: GlobalConfig
    servers: ServersConfig
    misc: MiscConfig
    flask: FlaskConfig

    def __init__(self, config):
        super().__init__({
            "glob": GlobalConfig(config["global"]),
            "servers": ServersConfig(config["servers"]),
            "misc": MiscConfig(config["misc"]),
            "flask": FlaskConfig(config["flask"]),
        })
