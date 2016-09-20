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

