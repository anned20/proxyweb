# ProxyWeb

Open Source Web UI for [ProxySQL](https://proxysql.com/)

![ProxyWeb ui](misc/images/ProxyWeb_main.jpg)

**Current features include**:
- Clean and responsive design
- [Multi-server support](misc/images/ProxyWeb_servers.jpg)
- [Configurable reporting](misc/images/ProxyWeb_report.jpg)
- Global and per-server options
- Hide unused tables (global or per-server basis)
- Sort content by any column (asc/desc)
- Online config editor
- Narrow-down content search
- Paginate content
- Command history and SQL dropdown menu
- Adhoc MySQL queries

# Setup

## Install ProxyWeb next to ProxySQL

With Docker:

```bash
docker run -h proxyweb --name proxyweb --network="host" -d proxyweb/proxyweb:latest
```
## Install it as a systemd service (Ubuntu)

```bash
git clone https://github.com/edmodo/proxyweb
cd proxyweb
make install
```

Visit  [http://ip_of_the_host:5000/setting/edit](http://ip_of_the_host:5000/setting/edit) first and adjust the credentials if needed.
The default connection is the local one with the default credentials.

## Install ProxyWeb to work with remote ProxySQL servers

### Configure ProxySQL for remote admin access

ProxySQL only allows local admin connections by default.

In order to enable remote connections you have to enable it in ProxySQL:

```sql
set admin-admin_credentials="admin:admin;radmin:radmin";
load admin variables to runtime; save admin variables to disk;
```

After this we can connect to the ProxySQL with:
- username: radmin
- password: radmin
- port: 6032 (default)

Run:
```bash
docker run -h proxyweb --name proxyweb -p 5000:5000 -d proxyweb/proxyweb:latest
```

or

```
git clone https://github.com/edmodo/proxyweb.git
cd proxyweb
make  proxyweb-run
```

Visit [http://ip_of_the_host:5000/setting/edit](http://ip_of_the_host:5000/setting/edit) first and edit the `servers`
section.

---

## Testing with docker-compose

Setting up a fully functional MySQL/ProxySQL/ProxyWeb/Orchestrator sandbox is super-easy with docker-compose:

```bash
git clone https://github.com/edmodo/proxyweb.git
cd proxyweb/docker-compose
make up
```

or

```bash
git clone https://github.com/edmodo/proxyweb.git
cd proxyweb
make  compose-up
```

This will start  the following services:

| Service       | Host Port                | Container           | Container port
| :---          | :---:                    | :---:               | :---:                  |
| MySQL source  | 23306                    | db1                 | 3306                   |
| MySQL replica | 23307                    | db2                 | 3306                   |
| MySQL replica | 23308                    | db3                 | 3306                   |
| MySQL replica | 23309                    | db4                 | 3306                   |
| ProxySQL      | admin: 16032, app: 13306 | proxysql_donor      | admin: 6032, app: 3306 |
| ProxySQL      | admin: 16033, app: 13307 | proxysql_satellite  | admin: 6032, app: 3306 |
| ProxySQL      | admin: 16034, app: 13308 | proxysql_standalone | admin: 6032, app: 3306 |
| Orchestrator  | 3000                     | orchestrator        | 3000                   |
| Goss          | 8000                     | goss                | 8000                   |
| ProxyWeb      | 5000                     | proxyweb            | 5000                   |


You can add sysbench to the test cluster, it runs on the preconfigured proxysql_standalone instance.

```bash
make sysbench-up
```

Or stop sysbench:

```bash
make sysbench-down
```

The sysbench output can be access with:
```bash
make sysbench-logs
```

After all the containers are up and  running, go to:
[http://127.0.0.1:5000/proxysql_donor/main/global_variables/](http://127.0.0.1:5000/proxysql_donor/main/global_variables//)

In this example we're going to set up ProxySQL with 4 MySQL backend servers with some basic query routing.
Once this is done, another ProxySQL server will be added as a [ProxySQL cluster](https://proxysql.com/blog/proxysql-cluster/)

### Configure the proxysql_donor:

You can start executing these, check the tables after each section:
```sql
-- configure the monitoring user:
UPDATE global_variables SET variable_value='monitor' WHERE variable_name='mysql-monitor_username';
UPDATE global_variables SET variable_value='monitor' WHERE variable_name='mysql-monitor_password';

-- Increase the timeouts so ProxySQL won't consider the backend servers unhealhy when stopping/starting the containers
UPDATE global_variables SET variable_value='2000' WHERE variable_name IN ('mysql-monitor_connect_interval','mysql-monitor_ping_interval','mysql-monitor_read_only_interval');
UPDATE global_variables SET variable_value='100' WHERE variable_name IN ('mysql-connect_retries_on_failure','monitor_ping_max_failures');

-- Don't add the source as a reader
UPDATE global_variables SET variable_value='false' WHERE variable_name = 'mysql-monitor_writer_is_also_reader';

LOAD MYSQL VARIABLES TO RUNTIME;
SAVE MYSQL VARIABLES TO DISK;

-- Create a replication hostgroup
INSERT INTO mysql_replication_hostgroups (writer_hostgroup,reader_hostgroup,comment) VALUES (1,2,'cluster1');

-- add the MySQL backend servers
INSERT INTO mysql_servers(hostgroup_id,hostname,port) VALUES (1,'db1',3306);
INSERT INTO mysql_servers(hostgroup_id,hostname,port) VALUES (1,'db2',3306);
INSERT INTO mysql_servers(hostgroup_id,hostname,port) VALUES (1,'db3',3306);
INSERT INTO mysql_servers(hostgroup_id,hostname,port) VALUES (1,'db4',3306);

LOAD MYSQL SERVERS TO RUNTIME;
SAVE MYSQL SERVERS TO DISK;

-- Add the MySQL user to the ProxySQL

INSERT INTO mysql_users(username,password,default_hostgroup) VALUES ('world','world',1);
LOAD MYSQL USERS TO RUNTIME;
SAVE MYSQL USERS TO DISK;

-- Set up a query rule that will send all ^SELECT to the reader hostgroup=2
INSERT INTO mysql_query_rules (rule_id,active,match_digest,destination_hostgroup,apply)
VALUES
(1,1,'^SELECT.*FOR UPDATE',1,1),
(2,1,'^SELECT',2,1);
LOAD MYSQL QUERY RULES TO RUNTIME;
SAVE MYSQL QUERY RULES TO DISK;
```

A basic ProxySQL setup with query routing is done, it's time to test it (run this from outside the docker containers):

```bash
mysql -vvv -uworld -pworld -P 13306 -h 127.0.0.1  world -e "insert into city (Name, CountryCode, District, Population) values ('Eger', 'HUN', 'Heves', 61234);"
```

```bash
mysql -vvv -uworld -pworld -P 13306 -h 127.0.0.1  world -e "select * from world.city where name = 'Budapest';"
```

You can observe that the select was redirected to the hostgroup=2 which is the reader.
http://127.0.0.1:5000/proxysql_donor/stats/stats_mysql_query_digest/

#### Let's setup the ProxySQL cluster:

Run the following on the  [proxysql_donor](http://127.0.0.1:5000/proxysql_donor/main/global_variables/) first THEN on the [proxysql_satellite](http://127.0.0.1:5000/proxysql_satellite/main/global_variables/).
The order is important as the 'satellite' node will start syncing the configs and it will also pull the runtime_proxysql_servers table.

```sql
UPDATE global_variables SET variable_value='radmin' WHERE variable_name = 'admin-cluster_username';
UPDATE global_variables SET variable_value='radmin' WHERE variable_name = 'admin-cluster_password';

LOAD ADMIN VARIABLES TO RUNTIME;
SAVE ADMIN VARIABLES TO DISK;

insert into proxysql_servers values ('proxysql_donor','6032','','donor');
LOAD PROXYSQL SERVERS TO RUNTIME;
SAVE PROXYSQL SERVERS TO DISK;
```

Check these proxysql_satellite runtime configs:
- [servers](http://127.0.0.1:5000/proxysql_satellite/main/runtime_mysql_servers/)
- [users](http://127.0.0.1:5000/proxysql_satellite/main/runtime_mysql_users/)
- [query_rules](http://127.0.0.1:5000/proxysql_satellite/main/runtime_mysql_query_rules/)
- [connection_pool](http://127.0.0.1:5000/proxysql_satellite/stats/stats_mysql_connection_pool/)

All the configs from the proxysql_donor are there.

Let's add a new rule to the [proxysql_donor](http://127.0.0.1:5000/proxysql_donor/main/mysql_query_rules/
):

```sql
INSERT INTO mysql_query_rules (active,match_digest,multiplex,cache_ttl) VALUES
('1','^SELECT @@max_allowed_packet',2,60000);
LOAD MYSQL QUERY RULES TO RUNTIME;
SAVE MYSQL QUERY RULES TO DISK;
```

The rule will appear in the proxysql_satellite [runtime_mysql_query_rules](http://127.0.0.1:5000/proxysql_satellite/main/runtime_mysql_query_rules/).

The proxysql_satellite is running on port 13307, you can start running  queries on this ProxySQL as well.
```bash
mysql -vvv -uworld -pworld -P 13307 -h 127.0.0.1  world -e "insert into city (Name, CountryCode, District, Population) values ('Eger', 'HUN', 'Heves', 61234);"

mysql -vvv -uworld -pworld -P 13307 -h 127.0.0.1  world -e "select * from world.city where name = 'Budapest';"
```

The proxysql_standalone ProxySQL instance have all the above (mysql_servers, user, routing) minus the cluster config readily available when it starts.

### Orchestrator

Orchestrator is running at http://127.0.0.1:3000

![Orchestrator](misc/images/orchestrator.jpg)

Discover the MySQL topology:

```bash
cd docker-compose && docker-compose exec orchestrator /usr/local/orchestrator/orchestrator -c discover -i db1
```

Or on the Orchestrator Web UI http://localhost:3000/web/discover

Failover demo video:

[![Sample Failover Video](https://img.youtube.com/vi/0LT4tfzXf58/0.jpg)](https://www.youtube.com/watch?v=0LT4tfzXf58)


Recreating the demo env is recommended:
```bash
make compose-down
make compose-up
```

### Goss

Goss is a YAML based serverspec alternative tool for validating a server’s configuration.
For the sake of simplicity a small web frontend was added in order to represent the health/status of our services.

It's running at  http://127.0.0.1:8000

Some  services  are in `failed` status initially as the purpose of this tutorial is to set the donor and satellite ProxySQLs up.
You can check if the setup was successful by visiting this page again.

The status checks are executed when the page is hit/reloaded.

![Goss](misc/images/goss.jpg)

---

## Miscellaneaous

#### List of parameters can be passed to the ProxyWeb Docker container

| Environment variable | Example value | Default |
| ---                  | ---           | ---     |
| WEBSERVER_PORT       | 8001          | 5000    |
| WEBSERVER_WORKERS    | 4             | 2       |
| WEBSERVER_THREADS    | 4             | 2       |

### Config file

example:
```yaml
servers:
  proxysql:
    dsn:
      - host: "127.0.0.1"
        user: "admin"
        passwd: "admin"
        port: "6032"
        db: "main"

#   proxysql_local_docker:
#     dsn:
#       - host: "host.docker.internal"
#         user: "admin"
#         passwd: "admin"
#         port: "6032"
#         db: "main"
#     hide_tables: [ 'mysql_aws_aurora_hostgroups', 'mysql_server_aws_aurora_failovers', 'mysql_server_aws_aurora_check_status', 'mysql_server_group_replication_log', 'mysql_galera_hostgroups', 'runtime_mysql_galera_hostgroups', 'mysql_server_aws_aurora_log' , 'mysql_server_aws_aurora_log', 'runtime_mysql_aws_aurora_hostgroups', 'runtime_mysql_server_aws_aurora_failovers', 'runtime_mysql_server_aws_aurora_check_status', 'runtime_mysql_server_group_replication_log', 'runtime_mysql_server_aws_aurora_log', 'runtime_mysql_server_aws_aurora_log', 'mysql_collations', 'mysql_firewall_whitelist_rules', 'mysql_firewall_whitelist_sqli_fingerprints', 'mysql_firewall_whitelist_users', 'mysql_query_rules_fast_routing', 'mysql_group_replication_hostgroups', 'restapi_routes', 'runtime_mysql_collations', 'runtime_mysql_firewall_whitelist_rules', 'runtime_mysql_firewall_whitelist_sqli_fingerprints', 'runtime_mysql_firewall_whitelist_users', 'runtime_mysql_query_rules_fast_routing', 'runtime_mysql_group_replication_hostgroups', 'runtime_restapi_routes', 'scheduler','mysql_server_galera_log' ]
#
#   proxysql_local_docker_no_host:
#     dsn:
#       - host: "172.17.0.1"
#         user: "radmin"
#         passwd: "radmin"
#         port: "6032"
#         db: "main"
#
#   proxysql_remote_read_only:
#     dsn:
#       - host: "10.0.0.1"
#         user: "radmin"
#         passwd: "radmin"
#         port: "6032"
#         db: "main"
#     read_only: true
#
#   #it's possible to hide tables that won't be used  - like aurora, galera related ones
#   proxysql_remote_with_hidden_tables:
#     dsn:
#       - host: "10.0.0.1",
#         user: "arthur",
#         passwd: "zaphod",
#         port: "6032",
#         db: "main"
#     hide_tables: [ 'mysql_aws_aurora_hostgroups', 'mysql_server_aws_aurora_failovers', 'mysql_server_aws_aurora_check_status', 'mysql_server_group_replication_log', 'mysql_galera_hostgroups', 'runtime_mysql_galera_hostgroups', 'mysql_server_aws_aurora_log' , 'mysql_server_aws_aurora_log', 'runtime_mysql_aws_aurora_hostgroups', 'runtime_mysql_server_aws_aurora_failovers', 'runtime_mysql_server_aws_aurora_check_status', 'runtime_mysql_server_group_replication_log', 'runtime_mysql_server_aws_aurora_log', 'runtime_mysql_server_aws_aurora_log', 'mysql_collations', 'mysql_firewall_whitelist_rules', 'mysql_firewall_whitelist_sqli_fingerprints', 'mysql_firewall_whitelist_users', 'mysql_query_rules_fast_routing', 'mysql_group_replication_hostgroups', 'restapi_routes', 'runtime_mysql_collations', 'runtime_mysql_firewall_whitelist_rules', 'runtime_mysql_firewall_whitelist_sqli_fingerprints', 'runtime_mysql_firewall_whitelist_users', 'runtime_mysql_query_rules_fast_routing', 'runtime_mysql_group_replication_hostgroups', 'runtime_restapi_routes', 'scheduler','mysql_server_galera_log' ]

misc:
  apply_config:
    - title: "LOAD EVERYTHING TO RUNTIME"
      info: "Load all config that is configured to the runtime datastructures. This means that the config will then be applied."
      sql: >-
        LOAD MYSQL USERS TO RUNTIME;
        LOAD MYSQL SERVERS TO RUNTIME;
        LOAD MYSQL QUERY RULES TO RUNTIME;
        LOAD MYSQL VARIABLES TO RUNTIME;
        LOAD ADMIN VARIABLES TO RUNTIME;
        LOAD PROXYSQL SERVERS TO RUNTIME;
        LOAD SCHEDULER TO RUNTIME;
    - title: "SAVE EVERYTHING TO DISK"
      info: "Save all config that is configured to disk. This means that it will be loaded whenever ProxySQL restarts."
      sql: >-
        SAVE MYSQL USERS TO DISK;
        SAVE MYSQL SERVERS TO DISK;
        SAVE MYSQL QUERY RULES TO DISK;
        SAVE MYSQL VARIABLES TO DISK;
        SAVE ADMIN VARIABLES TO DISK;
        SAVE PROXYSQL SERVERS TO DISK;
        SAVE SCHEDULER TO DISK;
    - title: "LOAD EVERYTHING FROM DISK"
      info: "Load all config that is configured on disk to memory. This resets the config in memory to the config on the disk. To then apply this to the runtime datastructures use \"LOAD EVERYTHING TO RUNTIME\"."
      sql: >-
        LOAD MYSQL USERS FROM DISK;
        LOAD MYSQL SERVERS FROM DISK;
        LOAD MYSQL QUERY RULES FROM DISK;
        LOAD MYSQL VARIABLES FROM DISK;
        LOAD ADMIN VARIABLES FROM DISK;
        LOAD PROXYSQL SERVERS FROM DISK;
        LOAD SCHEDULER FROM DISK;
  update_config:
    - title: "Add a new hostgroup"
      info: "Add a new hostgroup to the `mysql_replication_hostgroups` table.\\nhttps://proxysql.com/documentation/proxysql-configuration/"
      sql: "INSERT INTO `mysql_replication_hostgroups` (`writer_hostgroup`, `reader_hostgroup`, `comment`) VALUES (1, 2, 'cluster1');"

    - title: "Add a new MySQL/MariaDB server"
      info: "Add a new MySQL/MariaDB server to the `mysql_servers` table.\\nhttps://proxysql.com/documentation/proxysql-configuration/"
      sql: "INSERT INTO `mysql_servers` (`hostgroup_id`, `hostname`, `port`) VALUES (1, 'db1', 3306);"

    - title: "Add a new MySQL/MariaDB user"
      info: "Add a new MySQL/MariaDB user to the `mysql_users` table.\\nhttps://proxysql.com/documentation/proxysql-configuration/"
      sql: "INSERT INTO `mysql_users` (`username`, `password`, `default_hostgroup`, `max_connections`) VALUES ('world', 'world', 1, 200);"

    - title: "Add a new mysql_query_rule"
      info: "Add a new rule to the `mysql_query_rules` table.\\nhttps://proxysql.com/documentation/proxysql-configuration/"
      sql: "INSERT INTO `mysql_query_rules` (`rule_id`, `active`, `match_digest`, `destination_hostgroup`, `apply`) VALUES (1, 1, '^SELECT.*FOR UPDATE', 1, 1), (2, 1, '^SELECT', 2, 1);"

    - title: "Update a global config variable"
      info: "Modify a variable. \\nhttps://proxysql.com/documentation/proxysql-configuration/"
      sql: "set mysql-max_connections = '4096';"

  # The datatables javascript will order by desc by the first column so the first column the query return with should be the one in the order by expression
  adhoc_report:
    - title: "Top 10 SELECTs by sum_time"
      info: "Examining queries with big sum_time(number of execution * time to run) is a good place to start when optimizing queries."
      sql: "SELECT sum_time, digest, username, schemaname, SUBSTR(digest_text, 0, 80), count_star FROM stats_mysql_query_digest WHERE digest_text like 'SELECT%' ORDER BY sum_time DESC LIMIT 10;"

    - title: "Top 10 SELECTs by count_star"
      info: "Caching/rewriting/even removing frequently running queries can improve the overall performance significantly. ProxySQL supports all of these methods."
      sql: "SELECT count_star, digest, username, schemaname, SUBSTR(digest_text, 0, 80), sum_time FROM stats_mysql_query_digest WHERE digest_text like 'SELECT%' ORDER BY count_star DESC LIMIT 10;"

    - title: "Top 10 WRITE queries"
      info: "This helps identifying the most frequently running writes"
      sql: "SELECT count_star, digest, username, schemaname, SUBSTR(digest_text, 0, 80), sum_time FROM stats_mysql_query_digest where digest_text like 'INSERT%' or digest_text like 'DELETE%' or digest_text like 'UPDATE%' order by count_star DESC LIMIT 10;"

    - title: "Top 5 schemas by sum_time"
      info: "List of the schemas with the highest sum_time"
      sql: "SELECT sum(sum_time) as time_spent, schemaname FROM stats_mysql_query_digest group by schemaname order by time_spent desc limit 5;"

    - title: "Schemas with the most DMLs"
      info: "This helps identifying the schemas getting the most writes"
      sql: "SELECT sum(count_star) as sum_count_star, schemaname, sum(sum_time) as time_spent FROM stats_mysql_query_digest where digest_text like 'INSERT%' or digest_text like 'DELETE%' or digest_text like 'UPDATE%' group by schemaname order by time_spent desc;"

flask:
  SECRET_KEY: "12345678901234567890"
```

#### Global

The global `read_only` and `hide_tables` will be only used if they are not defined under the servers

| Variable       | Values                     | Effect
| :---           | :---:                      | :---:                                              |
| read_only      | true/false                 | Hides the sql editor                               |
| hide_tables    | array: ['table1','table2'] | Hides the tables from the ProxyWeb menus           |
| default_server | servers.${servername}      | Which server will be shown as default upon startup |

#### Servers

List of servers and credentials used for establish connection to ProxySQLs
The `read_only` and `hide_tables` variables added here have preference over the global one.

#### Misc

Configure the adhoc reports here

#### Flask

Used to configure Flask, don't touch.
A random `SECRET_KEY` is generated when using the dockerized ProxyWeb or when running `make install`.

### Features on the roadmap

- ability to edit tables
- authentication
- more advanced input validation

---

### Credits:

Thanks for Rene Cannao and the SysOwn team for the wonderful [ProxySQL](https://proxysql.com/).

ProxyWeb is using the following projects:
- Percona Server 5.7
- Bootstrap 4.4.1
- Mdbootstrap 4.16
- Font Awesome 5.8.2
- Google Fonts
- goss
- sysbench
