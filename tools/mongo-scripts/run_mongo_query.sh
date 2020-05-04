#!/bin/bash

# this authenticates against a mongodb and runs the query defined in 'run_mongo_query.js' and redirects the output to 'out_put.txt'
mongo copo_mongo -u copo_user -p 'enter-mongo-password-here' --authenticationDatabase admin --quiet run_mongo_query.js > out_put.txt