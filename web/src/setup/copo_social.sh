#!/usr/bin/env bash


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

file_env 'POSTGRES_PASSWORD'
file_env 'POSTGRES_USER'
file_env 'POSTGRES_DB'

file_env  'ORCID_SECRET'
file_env  'FACEBOOK_SECRET'
file_env  'TWITTER_SECRET'
file_env  'GOOGLE_SECRET'

if [ "$POSTGRES_USER" -a "$POSTGRES_PASSWORD" -a "$POSTGRES_DB" ]; then
    USER=${POSTGRES_USER}
	PASS=${POSTGRES_PASSWORD}
	DB=${POSTGRES_DB}
else
   exit 1
fi

export PGPASSWORD=$PASS
export PGUSER=$USER
export PGDATABASE=$DB
echo "Initialising social accounts in \"$DB\"..."

psql <<END_OF_SQL
 	DELETE FROM socialaccount_socialapp_sites;
 	DELETE FROM django_site;
 	DELETE FROM socialaccount_socialapp;
 	INSERT INTO django_site (id, domain, name) VALUES (1, 'www.copo-project.org', 'www.copo-project.org');
 	INSERT INTO socialaccount_socialapp (id, provider, name, client_id, secret, key) VALUES (1, 'google', 'Google', '197718904608-mubhgir39dr8e159ef4hb3l5i8me71b6.apps.googleusercontent.com', $GOOGLE_SECRET, ' ');
    INSERT INTO socialaccount_socialapp (id, provider, name, client_id, secret, key) VALUES (2, 'orcid', 'Orcid', 'APP-EGMH46B26C2OCJ9F', $ORCID_SECRET, ' ');
    INSERT INTO socialaccount_socialapp (id, provider, name, client_id, secret, key) VALUES (3, 'facebook', 'Facebook', '497282503814650', $FACEBOOK_SECRET, ' ');
    INSERT INTO socialaccount_socialapp (id, provider, name, client_id, secret, key) VALUES (4, 'twitter', 'Twitter', 'qrwJCJG9aBngGnBKrnvwgGNYc', $TWITTER_SECRET, ' ');
    INSERT INTO socialaccount_socialapp_sites (id, socialapp_id, site_id) VALUES (1,1,1);
    INSERT INTO socialaccount_socialapp_sites (id, socialapp_id, site_id) VALUES (2,2,1);
    INSERT INTO socialaccount_socialapp_sites (id, socialapp_id, site_id) VALUES (3,3,1);
    INSERT INTO socialaccount_socialapp_sites (id, socialapp_id, site_id) VALUES (4,4,1);
END_OF_SQL

echo "Social accounts initialised!"
