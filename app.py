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
from flask import Flask, render_template, request, session
from markupsafe import escape
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
config = mdb.get_config(config_file)
flask_config = config.flask.items()
for key, value in flask_config:
    app.config[key] = value


@app.route("/")
def dashboard():
    try:
        session.clear()

        config = mdb.get_config(config_file)

        server = config.glob.default_server
        session["history"] = []
        session["server"] = server
        session["dblist"] = mdb.get_all_dbs_and_tables(db, server)
        session["servers"] = mdb.get_servers()
        session["read_only"] = mdb.get_read_only(server)
        session["misc"] = mdb.get_config(config_file)["misc"]

        return render_template("dashboard.html", server=server)
    except Exception as e:
        raise ValueError(e)


@app.route("/<server>/")
@app.route("/<server>/<database>/<table>/")
def render_show_table_content(
    server,
    database="main",
    table="global_variables"
):
    try:
        # refresh the tablelist if changing to a new server

        if server not in session["dblist"]:
            session["dblist"].update(mdb.get_all_dbs_and_tables(db, server))

        session["servers"] = mdb.get_servers()
        session["server"] = server
        session["table"] = table
        session["database"] = database
        session["misc"] = mdb.get_config(config_file)["misc"]

        content = mdb.get_table_content(db, server, database, table)

        return render_template(
            "show_table_info.html",
            content=content,
            read_only=mdb.get_read_only(server),
        )
    except Exception as e:
        raise ValueError(e)


@app.route("/<server>/<database>/<table>/sql/", methods=["GET", "POST"])
def render_change(server, database, table):
    try:
        error = ""
        message = ""
        ret = ""
        session["sql"] = request.form["sql"]

        mdb.logging.debug(session["history"])
        select = re.match(r"^SELECT.*FROM.*$", session["sql"], re.M | re.I)

        if select:
            content = mdb.execute_adhoc_query(db, server, session["sql"])
            content["order"] = "true"
        else:
            ret = mdb.execute_change(db, server, session["sql"])
            content = mdb.get_table_content(db, server, database, table)

        if "ERROR" in ret:
            error = ret
        else:
            message = "Success"

        if (session["sql"].replace("\r\n", "") not in session["history"]
                and not error):
            session["history"].append(session["sql"].replace("\r\n", ""))

        return render_template(
            "show_table_info.html",
            content=content,
            error=error,
            message=message
        )
    except Exception as e:
        raise ValueError(e)


@app.route("/<server>/adhoc/")
def adhoc_report(server):
    try:
        adhoc_results = mdb.execute_adhoc_report(db, server)

        return render_template(
            "show_adhoc_report.html",
            adhoc_results=adhoc_results
        )
    except Exception as e:
        raise ValueError(e)


@app.route("/settings", methods=["GET", "POST"])
def render_settings():
    try:
        if request.method == "GET":
            config_file_content = ""

            with open(config_file, "r") as f:
                config_file_content = f.read()

            return render_template(
                "settings.html",
                config_file_content=config_file_content,
            )

        if request.method == "POST":
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
    except Exception as e:
        raise ValueError(e)


@app.errorhandler(Exception)
def handle_exception(e):
    print(e)
    return render_template("error.html", error=e), 500


@app.template_filter("nl2br")
def nl2br(value):
    """Converts newlines in text to HTML-tags"""
    result = "<br>".join(re.split(r"(?:\r\n|\r|\n)", escape(value)))

    return result


if __name__ == "__main__":
    app.run(host="0.0.0.0", use_debugger=False)
