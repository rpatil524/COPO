#FROM python:3.4
#RUN apt-get update && apt-get install -y \
#    rsync \
#    git \
#    libxml2-dev \
#    python \
#    build-essential \
#    make \
#    gcc \
#    python3-dev \
#    locales \
#    python-pip \
#    ruby-dev \
#    rubygems \
#    poppler-utils
#
#RUN gem install sass
#
#ENV PYTHONUNBUFFERED 0
#
#RUN mkdir /copo
#RUN mkdir /code
#
#WORKDIR /copo
#
#COPY web/src /code/
#RUN pip install -r /code/requirements/dev.txt
#
#ENTRYPOINT ["bash","-c","rsync -avhW --no-compress --progress /code/ /copo/ && rm -rf /code/ && python manage.py makemigrations rest && python manage.py makemigrations chunked_upload && python manage.py makemigrations && python manage.py migrate && python /copo/social.py && /usr/local/bin/gunicorn web.wsgi:application -w 4 -t 1000 -b :8000"]

FROM python:3.4
RUN apt-get update && apt-get install -y \
    git \
    libxml2-dev \
    python \
    build-essential \
    make \
    gcc \
    python3-dev \
    locales \
    python-pip \
    ruby-dev \
    rubygems \
    poppler-utils

RUN gem install sass

ENV PYTHONUNBUFFERED 0
RUN mkdir /copo
WORKDIR /copo

COPY src/requirements /copo/requirements
RUN pip install -r requirements/dev.txt

COPY src /copo/