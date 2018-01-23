# 19/1/2018 - FS
'''
The script installs COPO on a local development environment including all
necesary dependencies. When it has finished, you should be able to start a
local instance of COPO by going to the root directory and typing
"python mangage.py runserver"
'''
#import bug
#bug.trace()
import subprocess
import shlex
from string import Template
import sys

mongo_database = ""
mongo_user = ""
mongo_password = ""

def divider():
    print("\n" + 30*"=")

def execute(cmd):
    # this function is a wrapper used to call shell scripts
    cmd_array = shlex.split(cmd)

    # providing program name and args as array is preferred to passing single
    # string with shell=True as this is vulnerable to injection
    try:
        output = subprocess.Popen(cmd_array, stdout=subprocess.PIPE, universal_newlines=True)
    except Error:
        return Error
    return output


def get_user_supplied_parameters():
    mongo_database = raw_input("COPO MongoDB Database Name Should Be? (copo):\n")
    if not mongo_database:
        mongo_database = "copo"
    mongo_user = raw_input("COPO MongoDB User Should Be? (copo_user):\n")
    if not mongo_user:
        mongo_user = "copo_user"
    mongo_password = raw_input("COPO MongoDB Password Should Be?:\n")
    while not mongo_password:
        print("You must supply a password")
        mongo_password = raw_input("\n")
    postgres_database = raw_input("COPO Postgresql Database Name Should Be? (copo):\n")
    if not postgres_database:
        postgres_database = "copo"
    postgres_user = raw_input("COPO Postgresql User Should Be? (copo_user):\n")
    if not mongo_user:
        mongo_user = "copo_user"
    postgres_password = raw_input("COPO Postgresql Password Should Be?\n")
    while not postgres_password:
        print("You must supply a password")
        postgres_password = raw_input("\n")

    output = dict(
    {"mongo_database": mongo_database,
    "mongo_user": mongo_user,
    "mongo_password": mongo_password,
    "postgres_database": postgres_database,
    "postgres_user": postgres_user,
    "postgres_password": postgres_password
    })

    return output

def dummy():
    output = dict(
    {"mongo_database": "copo",
    "mongo_user": "copo_user",
    "mongo_password": "Apple123",
    "postgres_database": "copo",
    "postgres_user": "copo_user",
    "postgres_password": "Apple123"
    })
    return output


if __name__ == '__main__':
    print("")
    # variables
    platf = ""
    pac_man = ""

    # check os version
    import platform
    p = platform.platform()
    if "Darwin" in p:
        platf = "OSX"

        # check if brew installed
        out = execute("brew info")
        if out.returncode is None:
            pac_man = "brew"
        else:
            print("Homebrew Not Installed - Aborting")
            print("See https://brew.sh/")
            sys.exit()
    elif "Linux" in p:
        if "Ubuntu" in platform.linux_distribution()[0]:
            platf = "Ubuntu"
            pac_man = "apt-get"
        elif "CentOS" in platform.linux_distribution()[0]:
            platf = "CentOS"
            pac_man = "yum"




    print("You are running {} with {}.".format(platf, pac_man))

    print('{:>30}'.format("This script will install a development ready instance of COPO onto " \
        "your machine along with all its dependencies. If you are on a Mac, please " \
        "ensure you have Homebrew installed before running this script."))
    divider()
    # get user supplied variables
    #output = get_user_supplied_parameters()
    output = dummy()
    print(output)
