#!/bin/bash

sudo add-apt-repository ppa:deadsnakes/ppa # this is for legacy versions of python....only works on LTS versions of ubuntu
sudo apt-get update
sudo apt-get install -y software-properties-common \
default-jre \
rsync \
git \
nano \
libxml2-dev \
python \
build-essential \
make \
gcc \
python3.6-dev \
locales \
python3-pip \
ruby-dev \
rubygems \
poppler-utils \
postgresql \
redis \
vim \
gnupg

# install latest version of mongodb
wget -qO - https://www.mongodb.org/static/pgp/server-4.2.asc | sudo apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu bionic/mongodb-org/4.2 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-4.2.list
sudo apt-get install -y mongodb-org