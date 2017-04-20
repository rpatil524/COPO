FROM tutum/nginx

RUN rm /etc/nginx/sites-enabled/default
ADD sites-enabled/ /etc/nginx/sites-enabled

RUN mkdir /copo
COPY web/src /copo/
COPY web/src/static /www/static