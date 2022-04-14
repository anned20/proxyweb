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

from collections import defaultdict
from typing import Tuple
from flask import Flask, render_template, request, session
from markupsafe import escape
from lib.config import InvalidConfig, parse_config
import mdb
import re
import logging


logging.basicConfig(
    level=logging.WARN,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

app = Flask(__name__)

config_file = "config/config.yml"

db = defaultdict(lambda: defaultdict(dict))

# read/apply the flask config from the config file
try:
    config = mdb.get_config(config_file)
except InvalidConfig as e:
    logging.fatal(e)

    exit(1)

flask_config = config.flask.items()
for key, value in flask_config:
    app.config[key] = value


@app.route("/")
def dashboard() -> str:
    session.clear()

    config = mdb.get_config(config_file)

    server = config.glob.default_server
    session["history"] = []
    session["server"] = server
    session["dblist"] = mdb.get_all_dbs_and_tables(db, server)
    session["servers"] = mdb.get_servers()
    session["read_only"] = mdb.get_read_only(server)

    return render_template("dashboard.html", server=server)


@app.route("/<server>/")
@app.route("/<server>/<database>/<table>/")
def render_show_table_content(
    server,
    database="main",
    table="global_variables"
) -> str:
    # refresh the tablelist if changing to a new server

    if server not in session["dblist"]:
        session["dblist"].update(mdb.get_all_dbs_and_tables(db, server))

    session["servers"] = mdb.get_servers()
    session["server"] = server
    session["table"] = table
    session["database"] = database

    content = mdb.get_table_content(db, server, database, table)

    return render_template(
        "show_table_info.html",
        content=content,
        read_only=mdb.get_read_only(server),
        misc=mdb.get_config(config_file).misc
    )


@app.route("/<server>/<database>/<table>/sql/", methods=["GET", "POST"])
def render_change(server, database, table) -> str:
    error = ""
    message = ""
    stderr = ""
    session["sql"] = request.form["sql"]

    logging.debug(session["history"])
    select = re.match(r"^SELECT.*FROM.*$", session["sql"], re.M | re.I)

    if select:
        content = mdb.execute_adhoc_query(db, server, session["sql"])
        content["order"] = "true"
    else:
        _, stderr = mdb.execute_change(db, server, session["sql"])
        content = mdb.get_table_content(db, server, database, table)

    if "ERROR" in stderr:
        error = stderr
    else:
        message = "Success"

    if session["sql"].replace("\r\n", "") not in session["history"] and not error:
        session["history"].append(session["sql"].replace("\r\n", ""))

    return render_template(
        "show_table_info.html",
        content=content,
        error=error,
        message=message,
        misc=config.misc,
    )


@app.route("/<server>/adhoc/")
def adhoc_report(server) -> str:
    adhoc_results = mdb.execute_adhoc_report(db, server)

    return render_template(
        "show_adhoc_report.html",
        adhoc_results=adhoc_results
    )


@app.route("/settings", methods=["GET", "POST"])
def render_settings() -> str:
    if request.method == "GET":
        config_file_content = ""

        with open(config_file, "r") as f:
            config_file_content = f.read()

        return render_template(
            "settings.html",
            config_file_content=config_file_content,
        )

    if request.method == "POST":
        new_config = request.form["settings"]

        try:
            parse_config(new_config)

            with (
                open(config_file, "r") as src,
                open(config_file + ".bak", "w") as dest
            ):
                dest.write(src.read())

            with open(config_file, "w") as f:
                f.write(request.form["settings"])

            return render_template(
                "settings.html",
                message="success",
            )
        except InvalidConfig as e:
            return render_template(
                "settings.html",
                config_file_content=request.form["settings"],
                error=e
            )

    raise Exception("Wrong method")


@app.errorhandler(Exception)
def handle_exception(e) -> Tuple[str, int]:
    # Log the error and stacktrace.
    logging.exception(e)

    return render_template("error.html", error=e), 500


@app.template_filter("nl2br")
def nl2br(value) -> str:
    """Converts newlines in text to HTML-tags"""
    result = "<br>".join(re.split(r"(?:\r\n|\r|\n)", escape(value)))

    return result


if __name__ == "__main__":
    app.run(host="0.0.0.0", use_debugger=False)
