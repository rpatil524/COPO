#!/bin/bash

psql $POSTGRES_DB $POSTGRES_USER -c "DELETE FROM socialaccount_socialapp_sites"
psql $POSTGRES_DB $POSTGRES_USER -c "DELETE FROM django_site"
psql $POSTGRES_DB $POSTGRES_USER -c "DELETE FROM socialaccount_socialapp"
psql $POSTGRES_DB $POSTGRES_USER -c "INSERT INTO django_site (id, domain, name) VALUES (1, 'www.copo-project.org', 'www.copo-project.org')"
psql $POSTGRES_DB $POSTGRES_USER -c "INSERT INTO socialaccount_socialapp (id, provider, name, client_id, secret, key) VALUES (1, 'orcid', 'Orcid', '$ORCID_CLIENT_ID', '$ORCID_SECRET', '')"
psql $POSTGRES_DB $POSTGRES_USER -c "INSERT INTO socialaccount_socialapp_sites (id, socialapp_id, site_id) VALUES (1, 1, 1)"