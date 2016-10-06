#!/usr/bin/env python3
__author__ = 'tonietuk'

import subprocess
import shutil
import time


def check_status(process_name, display_name):
    process = subprocess.Popen(["pgrep", process_name], stdout=subprocess.PIPE)
    out, err = process.communicate()
    if not err:
        if len(out.decode("utf-8")) > 0:
            return 0  # service running
        else:
            return 1  # service not running
    else:
        return -1  # can't determine service status


def start_service(process_name, display_name, starters):
    status = check_status(process_name, display_name)
    if status == 0:
        print(display_name + " is running.")
    elif status == 1:
        sub_status = 1
        print("Attempting to start " + display_name + "...")
        args = ["nohup", "python3", "managedp.py",""]
        for s in starters:
            args[3] = s
            process = subprocess.Popen(args, stdout=subprocess.PIPE)
            time.sleep(2)  # give some time for the called process to run
            sub_status = check_status(process_name, display_name)
            if sub_status == 0:
                print(display_name + " successfully started!")
                break
        if sub_status == 1:
            print("Error: couldn't start " + display_name + ".")
        elif status == -1:
            print(display_name + " - can't determine service status!")


# create a list of starting procedures/paths to services
mysql_starters = [
    "/usr/local/mysql/support-files/mysql.server start",
    "mysql.server start",
    shutil.which("mysql") + ".server start",
    "mysqld", 
    "mysqld_safe", 
    "/etc/init.d/mysql start",
    "service mysqld start",
    "feel-free-to-append-to-this-list"
    ]

redis_starters = [
    "/usr/bin/redis-server",
    shutil.which("redis-server"),
    "feel-free-to-append-to-this-list"
    ]

mongo_starters = [
    "/usr/bin/mongod",
    shutil.which("mongod"),
    "feel-free-to-append-to-this-list"
    ]

# start_service("mysql", "MySQL server", mysql_starters)
start_service("redis-server", "Redis server", redis_starters)
start_service("mongod", "MongoDB", mongo_starters)
