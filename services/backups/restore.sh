#!/usr/bin/env bash

#*********************************************************************************
# before running this restore scripts run the following on the postgres db host: *
# dropdb copo -U copo_user                                                       *
# createdb copo -U copo_user                                                     *
# Also, supply restore paths for both mongo and postgres                         *
#*********************************************************************************


# usage: file_env VAR [DEFAULT]
#    ie: file_env 'XYZ_DB_PASSWORD' 'example'
# (will allow for "$XYZ_DB_PASSWORD_FILE" to fill in the value of
#  "$XYZ_DB_PASSWORD" from a file, especially for Docker's secrets feature)
file_env() {
    local var="$1"
    local fileVar="${var}_FILE"
    local def="${2:-}"
    if [ "${!var:-}" ] && [ "${!fileVar:-}" ]; then
        echo >&2 "error: both $var and $fileVar are set (but are exclusive)"
        exit 1
    fi
    local val="$def"
    if [ "${!var:-}" ]; then
        val="${!var}"
    elif [ "${!fileVar:-}" ]; then
        val="$(< "${!fileVar}")"
    fi
    export "$var"="$val"
    unset "$fileVar"
}

file_env 'MONGO_DB'
file_env 'MONGO_HOST'
file_env 'MONGO_PORT'
file_env 'MONGO_INITDB_ROOT_USERNAME'
file_env 'MONGO_INITDB_ROOT_PASSWORD'
file_env 'POSTGRES_DB'
file_env 'POSTGRES_USER'
file_env 'POSTGRES_PORT'
file_env 'POSTGRES_SERVICE'
file_env 'POSTGRES_PASSWORD'

echo "Restoring mongo \"$MONGO_DB\"..."
# run mongo restore
mongorestore --db ${MONGO_DB} -u copo_admin -p ${MONGO_INITDB_ROOT_PASSWORD} --authenticationDatabase admin -h ${MONGO_HOST}:${MONGO_PORT} --drop /backup/mongo/20190521030000/copo_mongo

echo "Restoring postgres \"$POSTGRES_DB\"..."
PGPASSWORD=${POSTGRES_PASSWORD} psql -h ${POSTGRES_SERVICE} -p ${POSTGRES_PORT} -U ${POSTGRES_USER} -d ${POSTGRES_DB} < backup/postgres/20190521220228.sql