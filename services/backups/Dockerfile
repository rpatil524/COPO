FROM alpine:edge

RUN apk update
RUN apk upgrade
RUN apk add bash

RUN apk add mongodb-tools
RUN apk add postgresql-client

# create backup directories
RUN mkdir -p /backup/mongo
RUN mkdir -p /backup/postgres

# set up cron jobs
ADD crontab.txt /crontab.txt
ADD script.sh /script.sh

COPY entry.sh /entry.sh
RUN chmod 755 /script.sh /entry.sh

RUN /usr/bin/crontab /crontab.txt

CMD ["/entry.sh"]
