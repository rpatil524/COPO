#!/bin/bash

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

if [ $opsys == "Darwin" ]
then
  # install python3
  $pac_man install python3
  # install MongoDB
  $pac_man install mongodb
  echo making data/db/
  sudo mkdir -p /data/db
  brew services start mongodb
  # install redis
  $pac_man install redis
  $pac_man services start redis
  # install postgres
  $pac_man install postgresql
  $pac_man services start postgresql
elif [ $opsys == "Ubuntu" ]
then
  $pac_man --allow-unauthenticated -y install python3
  # import public key used by apt-get
  $pac_man install apt-transport-https
  apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 2930ADAE8CAF5059EE73BB4B58712A2291FA4AD5
  # create list file for MongoDB
  echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu xenial/mongodb-org/3.6 multiverse" | tee /etc/apt/sources.list.d/mongodb-org-3.6.list
  $pac_man update
  # install and start mongo
  $pac_man install -y mongodb-org
  mongod --fork --config /etc/mongod.conf
  # install and start redis
  $pac_man install redis-server
  service redis-server start
fi
