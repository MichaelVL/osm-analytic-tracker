FROM debian:jessie
#FROM resin/rpi-raspbian

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get -y update && apt-get install -y supervisor git python python-pip python-shapely python-tz python-dev mongodb nginx

RUN mkdir -p /data/db

ADD html /html
RUN mkdir /html/jquery-2.1.3
ADD https://code.jquery.com/jquery-2.1.3.min.js /html/jquery-2.1.3/jquery.min.js

RUN mkdir -p /html/leaflet-0.7.7
ADD http://cdn.leafletjs.com/leaflet/v0.7.7/leaflet.css  /html/leaflet-0.7.7/leaflet.css
ADD http://cdn.leafletjs.com/leaflet/v0.7.7/leaflet.js /html/leaflet-0.7.7/leaflet.js

RUN mkdir -p /html/dynamic && chown -R www-data:www-data /html

COPY docker/config/nginx.conf /etc/nginx/nginx.conf
COPY docker/config/nginx-osmtracker.conf /etc/nginx/sites-enabled/default

RUN apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN mkdir /osmtracker
ADD requirements.txt /osmtracker/
RUN pip install -r /osmtracker/requirements.txt

WORKDIR /osmtracker/osm-analytic-tracker
# Override requirements.txt for osmapi
RUN git clone https://github.com/MichaelVL/osmapi.git
#ADD denmark.poly region.poly
ADD http://download.geofabrik.de/europe/denmark.poly region.poly

ADD *.py config.json logging.conf worker.sh ./
RUN mkdir /osmtracker/templates
ADD templates templates/
RUN sed -i 's/"path": "html"/"path": "\/html\/dynamic"/' ./config.json

EXPOSE 80

ADD supervisord.conf /
CMD ["/usr/bin/supervisord", "-c", "/supervisord.conf"]
