## COPO Deployment with Docker

Featuring:

- Docker Engine
- Docker Compose
- Python 3.4
- Django
- Mongo DB
- Postgres
- Nginx
- Gunicorn


### Deployment Instructions

### OS X 

1. Start new machine - `docker-machine create -d virtualbox dev;`
2. Build images - `docker-compose build`
3. Start services - `docker-compose up -d`
4. Grab IP - `docker-machine ip dev` - and view in your browser


### Linux - Ubuntu

1. edit/create /etc/apt/sources.list.d/docker.list
    - add line `deb https://apt.dockerproject.org/repo ubuntu-xenial main`
    - above change 'ubuntu-*' for your version of ubuntu
2. update apt - `sudo apt-get update`
3. install docker - `sudo apt-get install docker-engine`
4. install docker-compose - `sudo apt-get install docker-compose`
5. pull latest version of COPO `git clone -b deployment https://github.com/collaborative-open-plant-omics/COPO.git`
6. Build images - `docker-compose build`
7. Start services - `docker-compose up -d`