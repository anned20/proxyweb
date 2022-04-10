#!/usr/bin/python3

"""ProxyWeb - A Proxysql Web user interface

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.
This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with
this program. If not, see <http://www.gnu.org/licenses/>.
"""

__author__ = "Miklos Mukka Szel"
__contact__ = "miklos.szel@edmodo.com"
__license__ = "GPLv3"


from typing import Any, Dict, List, Tuple
import mysql.connector
from mysql.connector.connection import MySQLConnection, MySQLCursor
import logging
import subprocess
from lib import config
from models import Config, Server


def get_config(file: str = "config/config.yml") -> Config:
    cfg = config.parse_config_file(file)

    return cfg


def db_connect(
    db,
    server: str,
    autocommit: bool = False,
    buffered: bool = False,
    dictionary: bool = True
) -> Tuple[MySQLConnection, MySQLCursor]:
    config = get_config()
    db["cnf"] = config

    server_config = config.servers[server].dsn
    logging.debug(server_config)

    conn = mysql.connector.connect(
        **server_config,
        raise_on_warnings=True,
        get_warnings=True,
        connection_timeout=3
    )

    if conn.is_connected():
        logging.debug(f"Connected to {server_config.db} as {server_config.user} on {server_config.host}")

    conn.autocommit = autocommit
    conn.get_warnings = True

    cursor = conn.cursor(
        buffered=buffered,
        dictionary=dictionary
    )

    logging.debug(f"Buffered: {buffered}, dictionary: {dictionary}, autocommit: {autocommit}")

    return conn, cursor


def get_all_dbs_and_tables(db, server: str) -> Dict[str, Dict[str, List[str]]]:
    all_dbs = {server: {}}

    conn, cur = db_connect(db, server=server)

    try:
        cur.execute("SHOW DATABASES")

        table_exception_list = db["cnf"]["glob"]["hide_tables"] if "hide_tables" in db["cnf"]["glob"] else []

        if db["cnf"]["servers"][server]["hide_tables"]:
            table_exception_list += db["cnf"]["servers"][server]["hide_tables"]

        for database in cur.fetchall():
            all_dbs[server][database["name"]] = []

            cur.execute(f"SHOW TABLES FROM {database['name']}")
            for table in cur.fetchall():
                # hide tables as per global or per server config
                if table["tables"] not in table_exception_list:
                    all_dbs[server][database["name"]].append(table["tables"])
    finally:
        conn.close()

    return all_dbs


def get_table_content(db, server: str, database: str, table: str) -> Dict[str, Any]:
    """returns with a dict with two keys
    "column_names" = list and rows = tuples"""
    content = {}

    logging.debug("server: {} - db: {} - table:{}".format(
        server,
        database,
        table
    ))

    conn, cur = db_connect(db, server=server, dictionary=False)

    try:

        string = "SELECT * FROM {}.{} ORDER BY 1".format(database, table)
        logging.debug("query: {}".format(string))

        cur.execute(string)

        content["rows"] = cur.fetchall()
        content["column_names"] = [
            i[0] for i in cur.description
        ]
    finally:
        conn.close()

    return content


def execute_adhoc_query(db, server: str, sql: str) -> Dict[str, Any]:
    """returns with a dict with two keys
    "column_names" = list and rows = tuples"""
    content = {}

    logging.debug("server: {} - sql: {}".format(server, sql))

    conn, cur = db_connect(db, server=server, dictionary=False)

    try:
        cur.execute(sql)

        content["rows"] = cur.fetchall()
        content["column_names"] = [
            i[0] for i in cur.description
        ]
    finally:
        conn.close()

    return content


def execute_adhoc_report(db, server: str) -> List[Dict[str, Any]]:
    """returns with a dict with two keys
    "column_names" = list and rows = tuples"""
    adhoc_results = []

    conn, cur = db_connect(db, server=server, dictionary=False)

    try:
        config = get_config()

        if "adhoc_report" in config.misc.categories:
            for item in config.misc.categories["adhoc_report"].queries:
                cur.execute(item.sql)

                adhoc_results.append({
                    "title": item.title,
                    "sql": item.sql,
                    "info": item.info,
                    "column_names": [
                        i[0] for i in cur.description
                    ],
                    "rows": cur.fetchall()
                })
        else:
            pass
    finally:
        conn.close()

    return adhoc_results


def get_servers() -> List[Server]:
    proxysql_servers = []

    try:
        servers_dict = get_config()

        for server in servers_dict.servers:
            proxysql_servers.append(server)

        return proxysql_servers
    except Exception:
        raise ValueError("Cannot get the serverlist from the config file")


def get_read_only(server) -> bool:
    try:
        config = get_config()

        if config.glob.read_only:
            return True

        if server in config.servers:
            if config.servers[server].read_only:
                return True

        return False
    except Exception:
        raise ValueError("Cannot get read_only status from the config file")


def execute_change(db, server: str, sql: str) -> Tuple[str, str]:
    # this is a temporary solution as using the mysql.connector for
    # certain writes ended up with weird results, ProxySQL is not a MySQL
    # server after all. We're investigating the issue.

    dsn = get_config().servers[server].dsn
    cmd = ("mysql -h %s -P %s -u %s -p%s main -e '%s'" % (
        dsn["host"],
        dsn["port"],
        dsn["user"],
        dsn["passwd"],
        sql
    ))
    p = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, stderr = p.communicate()

    return stdout.decode(), stderr.decode().replace(
        "".join([
            "mysql: [Warning] Using a password on the",
            " command line interface can be insecure.\n"
        ]),
        ""
    )
