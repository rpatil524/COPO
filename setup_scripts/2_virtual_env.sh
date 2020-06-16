#!/bin/bash
pip3 install virtualenv==16.7.10
virtualenv -p python3.6 ../venv
source ../venv/bin/activate
which pip3
pip3 install -r ../requirements/base.txt