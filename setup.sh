#!/bin/bash

postgres_user='postgres_user'
postgres_db='copo'
postgres_pw='Apple123'
vmname="copo_env"

python -c "exit"
if [ "$?" -eq 127 ]
then
  echo "Python not found on this system. Please install any version of python and try again"
  exit
fi

divider() {
  s=$(printf "%-30s" "-")
  echo "${s// /-}"
}
div=divider
# embedded python function to get system info
function check_os {
python - <<END
# check os version
import platform
p = platform.platform()
if "Darwin" in p:
    print("Darwin")
elif "Linux" in p:
    if "Ubuntu" in platform.linux_distribution()[0]:
        print("Ubuntu")
    elif "CentOS" in platform.linux_distribution()[0]:
        print("CentOS")
END
}


# START
printf 'Welcome to the installation program for COPO. This will install a development ready instance of COPO onto
your machine along with all its dependencies. This script is only garanteed to work on OSX and Ubuntu installations'

$div

opsys=$(check_os)
printf 'Determining OS: %s\n' "$opsys"
me=$(whoami)
printf 'Installing under user accoutn: %s\n' "$me"
printf 'Checking Package Manager\n'

if [ $opsys == "Darwin" ]
then
  brew info
  if [ "$?" -eq 127 ]
  then
    # brew not installed so install it and update
    printf "installing homebrew\n"
    /usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
    brew update
    pac_man='brew'
  else
    # brew is installed now update
    pac_man='brew'
  fi
elif [ $opsys == "Ubuntu" ]
then
  pac_man='apt-get'
elif [ $opsys == "CentOS" ]
then
  pac_man='yum'
fi
printf "updating packages\n"
$pac_man update


# first determine the current OS
os=check

# now check dependencies are installed
$pac_man install -y git
if [ $opsys == "Darwin" ]
then
  # install python3
  $pac_man install -y python3
  # install MongoDB
  $pac_man install -y mongodb
  echo making data/db/
  sudo mkdir -p /data/db
  brew services start mongodb
  # install redis
  $pac_man install redis
  $pac_man services start redis
  # install postgres
  $pac_man install postgresql
  $pac_man services start postgresql
  # create psql user and db
  sudo -u $me createuser $postgres_user
  sudo -u $me createdb $postgres_db
  psql postgres $me -c "alter user $postgres_user with encrypted password '$postgres_pw';"
  psql postgres $me -c "grant all privileges on database $postgres_db to $postgres_user ;"
  # install virtual env
  pip3 install virtualenv
  virtualenv -p python3 $vmname
  source $vmname/bin/activate
  pip3 install --upgrade setuptools
  pip3 install -r /COPO/web/src/requirements/base.txt
elif [ $opsys == "Ubuntu" ]
then
  $pac_man --allow-unauthenticated install -y python3
  # import public key used by apt-get
  $pac_man install -y apt-transport-https
  apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 2930ADAE8CAF5059EE73BB4B58712A2291FA4AD5
  # create list file for MongoDB
  echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu xenial/mongodb-org/3.6 multiverse" | tee /etc/apt/sources.list.d/mongodb-org-3.6.list
  $pac_man update
  # install and start mongo
  $pac_man install -y mongodb-org
  # need to start mongo without auth, make admin user and copo_user, then
  # restart with auth
  mongod --fork --config /etc/mongod.conf
  mongo localhost/admin --eval "db.createUser({user: 'admin', pwd: 'copo_admin', roles:[{ role: 'userAdminAnyDatabase', db: 'admin' } ]});"
  mongo localhost/admin --eval "db.createUser({user: 'copo_user', pwd: 'Apple123', roles:[{ role:'readWrite', db: 'copo_mongo' }]})"
  mongo localhost/admin --eval "db.shutdownServer()"
  mongod --fork --auth --config /etc/mongod.conf
  # install and start redis
  $pac_man install -y redis-server
  service redis-server start
  $pac_man install -y postgresql postgresql-contrib python-psycopg2 libpq-dev
  service postgresql start
  # install sudo for postgres setup
  $pac_man install -y sudo
  # TODO change thse later for user input strings
  # create psql user and db
  $pac_man install sed
  # need to change postgres to password authentication
  sed -i 's/peer/md5/g' /etc/postgresql/$(ls /etc/postgresql)/main/pg_hba.conf
  sudo -u postgres createuser $postgres_user
  sudo -u postgres createdb $postgres_db
  sudo -u postgres psql -c "alter user $postgres_user with encrypted password '$postgres_pw';"
  sudo -u postgres psql -c "grant all privileges on database $postgres_db to $postgres_user;"
  # install venv
  $pac_man install -y python-setuptools
  easy_install pip
  $pac_man -y install python3-pip
  pip3 install virtualenv
  virtualenv -p python3 $vmname
  source $vmname/bin/activate
  pip3 install --upgrade setuptools
  pip3 install -r /COPO/web/src/requirements/base.txt
fi
