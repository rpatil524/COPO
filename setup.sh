#!/bin/bash

divider() {
  s=$(printf "%-30s" "-")
  echo "${s// /-}"
}

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



div=divider

printf 'This script will install a development ready instance of COPO onto
your machine along with all its dependencies. If you are on a Mac, please
ensure you have Homebrew installed before running this script.\n'

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
