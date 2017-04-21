#!/usr/bin/env bash

if [ "$MONGO_USER" != "" ] && [ "$MONGO_USER_PASSWORD" != "" ] && [ "$MONGO_INITDB_ROOT_USERNAME" != "" ] && [ "$MONGO_INITDB_ROOT_PASSWORD" != "" ]
then
   	USER=${MONGO_USER}
	PASS=${MONGO_USER_PASSWORD}
	ADMIN_USER=${MONGO_INITDB_ROOT_USERNAME}
	ADMIN_PASS=${MONGO_INITDB_ROOT_PASSWORD}
else
   exit 1
fi

DB=${MONGO_DB:-admin}
ROLE=readWrite

echo "creating Mongo user: \"$USER\"..."
mongo admin -u $ADMIN_USER -p $ADMIN_PASS --eval "db.createUser({ user: '$USER', pwd: '$PASS', roles: [ { role: '$ROLE', db: '$DB' } ] });"

echo "Mongo user created!"




