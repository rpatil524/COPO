#!/bin/bash
MONGO_USER=copo_user
MONGO_PASSWORD=password
mongo localhost/admin --eval "db.createUser({user: '$MONGO_USER', pwd: '$MONGO_PASSWORD', roles:[{ role:'readWrite', db: 'copo_mongo' }]})"