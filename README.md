## COPO Deployment with Docker

Featuring:

- Docker Engine
- Docker Swarm
- Python 3.5
- Django 2.x
- Mongo DB
- Postgres
- Nginx
- Gunicorn


[Check out the documentation!](http://copo-project.readthedocs.io/en/latest/)

For local installation:

* the following instructions assume the following pre-requisites
	* you have created an app in ORCiD, and have the Client Key and Client Secret
	* you have creates a user in the ENAs Webin system and have the Username and Password

* ensure docker is installed and running

* ensure docker-compose is installed

* create a directory and add the following files
    * copo_mongo_initdb_root_password
    * copo_mongo_user_password
    * copo_postgres_user_password
    * copo_web_secret_key
    * copo_orcid_secret_key
    * copo_figshare_consumer_secret_key
    * copo_figshare_client_id_key
    * copo_figshare_client_secret_key
    * copo_google_secret_key
    * copo_twitter_secret_key
    * copo_facebook_secret_key
    * copo_webin_user
    * copo_webin_user_password
    - these can all contain random alpha-numeric strings apart from copo_webin_user, copo_webin_user_password and copo_orcid_Secret_key which should contain the details described above.
* in the secrets section of docker-compose.yml, change "$(COPO_KEYS)" to the directory path you created in the previous step

* in a terminal, navigate to the root of this project

* type "docker-compose up"
    * if you receive errors about permissions, add you user to the docker group
        * type "sudo usermod -aG docker $(whoami)"
        * log out and log in again
    * if you receive errors about docker not running, start the docker daemon
        * type "sudo service docker start"
	
* assuming everything has worked, you will eventually see the message
	* copo-web_1       | Starting ASGI/Channels version 2.2.0 development server at http://0.0.0.0:8000/

* navigate in a browser to 127.0.0.1:8000/copo


[![DOI](https://zenodo.org/badge/31064842.svg)](https://zenodo.org/badge/latestdoi/31064842)

