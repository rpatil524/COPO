FROM python:3.6
ENV PYTHONUNBUFFERED 0

RUN apt-get update && apt-get install -y \
    rsync \
    git \
	nano \
    libxml2-dev \
    python \
    build-essential \
    make \
    gcc \
    python3-dev \
    locales \
    python3-pip \
    ruby-dev \
    rubygems \
    poppler-utils

RUN gem install sass

COPY ./requirements/ /tmp/requirements/
RUN pip3 install -r /tmp/requirements/dev.txt

WORKDIR /copo
COPY . /copo/

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

#ENTRYPOINT ["bash","-c","python manage.py makemigrations rest && python manage.py makemigrations chunked_upload && python manage.py makemigrations && python manage.py migrate && python manage.py social_accounts && python manage.py setup_groups && python manage.py setup_schemas && python manage.py runserver 0.0.0.0:8000"]