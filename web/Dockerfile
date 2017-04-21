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
    rubygems \
    poppler-utils

RUN gem install sass

ENV PYTHONUNBUFFERED 0
RUN mkdir /copo
WORKDIR /copo

COPY web/src/requirements /copo/requirements
RUN pip install -r requirements/dev.txt

COPY web/src /copo/
