## OpenStreetMap Analytic Difference Engine

[![CircleCI](https://circleci.com/gh/MichaelVL/osm-analytic-tracker.svg?style=svg)](https://circleci.com/gh/MichaelVL/osm-analytic-tracker)

OpenStreetMap Analytic Difference Engine is an analytic live (web) service for
OpenStreetMap (OSM) edits.  Edits are analysed and presented with a concise
summary.  The (text-based) summary is designed to provide a good insight into
what each changeset comtains (what was added, changed or deleted) and an
optional visual-diff provides insight into the geographical changes of each
changeset.

This live service is different from other OpenStreetMap live services in that it
focus on being analytic and less on being visual.

A running demo can be seen on https://osm.expandable.dk. Read below for the
details about the service. For deployment, see the [Kubernetes
deployment](kubernetes/README.md).

The purpose of this tool is:

1. Prof-of-concept for an improved changeset-info service (improved compared to looking up changeset details on http://openstreetmap.org)
2. Provide insight into changes in your area of interest
3. Improve team spirit of a regional OSM team/task-force.
4. Quality ensurance through peer review
5. Learning by seeing how other make edits to your region of interest.

The service is available as a web-service and provide three different information elements:

1. An overall summary with a overview map containing bounding boxes of recent edits
2. A list of changesets with analytic details
3. A visual diff for the changes of each changeset

### Summary

The main page contain this overview in the top with OSM-user specific
colour-coded bounding boxes for each changeset and text-based summary for the
tracked time peried.

![Image](doc/summ2.png?raw=true)

### List of Changesets with changes

Green show added tags and how many additions the changeset contained.  Yellow show changed tags and red show deleted tags.

![Image](doc/csets.png?raw=true)

### Visual Diff

Geographical changes in the changeset, green are added objects, blue changed and red deleted. Each element can be clicked for more details.

![Image](doc/vdiff3.png?raw=true)
![Image](doc/vdiff.png?raw=true)

## How Does It Work?

TL;DR:

Run it using Docker:

```
docker run -p 8080:80 -e OSMTRACKER_REGION="/osm-regions/denmark.poly" -e OSMTRACKER_MAP_SCALE="6" michaelvl/osmtracker-all-in-one
```

and point your browser to 127.0.0.1:8080. This docker image contain all
necessary services to demonstrate the analytic tracker, including two worker
instances. It is however not a good example of a 'production' deployment.  For
production-class deployments take a look at the [Kubernetes deployment](kubernetes/README.md)
in the kubernetes folder.

### Using an alternative config

The multi-dimensional labeling system described below allows for quite advanced
configurations, however, the most typical configuration is to change the focus
region and the scale of the default map. This can be done by setting the
environment variables OSMTRACKER_REGION and OSMTRACKER_MAP_SCALE.  See the
[regions.txt](docker/regions.txt) for available regions in the pre-build images.

Using a full custom config file can be done as follows:

```
curl -O https://raw.githubusercontent.com/MichaelVL/osm-analytic-tracker/master/config.json
mkdir osmtracker-config
mv config.json osmtracker-config/
sed -i 's/"path": "html"/"path": "\/html\/dynamic"/' osmtracker-config/config.json
docker run -p 8080:80 -v <path>/osmtracker-config:/osmtracker-config osmtracker-all-in-one
```

### Labels and filters

Changesets are filtered using a labeling system and labels can also be used in
backends for generating different views into the changesets.  The following
excerpt from the config file illustrates some possibilities with labels.
Initially the 'pre_labels' section is executed.  Currently two types are tests
are implemented; An area-based test and a regular expression-based test (which
can test on all fields of a changeset, including tags on changes).  If an area
or regex test is found be succeed, the associated label is applied to the
changeset.

The config below specify to mark changesets inside 'region.poly' with labels
'inside-area' and 'center-inside-area' (with a small difference in how 'inside'
is defined). Also, if the changeset comment has a '#' followed by some text, it
will be labeled with 'mapping-event'.

The definition of 'prefilter_labels' below defines that all changesets which do
not have the three labels are to be dropped. Generally the 'prefilter_labels'
definition use an AND between the inner list and an OR on the outer list,
i.e. '[['foo', 'bar'], ['baz']]' would mean that a changeset should have labels
'foo' and 'bar' OR 'baz'.

```
	"pre_labels": [
	    {"area_file": "region.poly", "area_check_type": "cset-bbox", "label": "inside-area"},
	    {"area_file": "region.poly", "area_check_type": "cset-center", "label": "center-inside-area"},
	    {"regex": [{".meta.tag.comment": ".*#\\w+"}], "label": "mapping-event"}
	],
	"prefilter_labels": [["inside-area", "center-inside-area", "mapping-event"]],
```

Note that 'prefilter_labels' regex can only operate on changeset
metadata. Labeling on changeset content is done using 'post_labels' as seen from
the following config except. This labels changesets which has changes with tag
'osak:identifier' and any tag value (this indicates changes of imported Danish
address nodes).

```
	"post_labels": [
	    {"regex": [{".changes.tag.osak:identifier": ""}], "label": "address-node-change"}
	],
```

Format of regex on changes are:

```
        .changes[.action][.element-type].elements
```

where optional '.action' is either '.modify', '.create' or '.delete' and
optional '.element-type' is either '.node', '.way' or '.relation'.  The address
change example above does not specify any action or element type i.e. any change
of any element type will match.


### Architecture

The general architecture is shown below. See also the [Kubernetes
architecture](kubernetes/README.md).

![Image](doc/architecture.png?raw=true)

### Components

- osmtracker.py  The core functionality with multiple roles depending on arguments.
- apiserver.py  An API server providing access to the database. The
  OpenAPI/Swagger API specicication is in [apispec.yaml](apiserver/apispec.yaml).
- elastic-gw.py  An ElasticSearch sync componentat which pushes changesets to ElasticSearch.
- db.py   MongoDB backend for storing changeset information
- messagebus.py Am AMQP (RabbitMQ) messagebus for interconnection components.
- osm/changeset.py  The class which contain the main analysis code.

The osmtracker.py script tracks OpenStreetMap minutely diffs and optionally
filters them through a bounding-box polygon (country-based polygons can be found
on http://download.geofabrik.de/).  Changesets found to be within the area of
interest are analysed further and a number of backends generate output.  The
HTML backends provide HTML data which can be served through a web-server.  The
client-side parts include a javascript-based poll feature that will update the
changeset list whenever it changes (special care has been taken to minimize
network load).

Configuration is provided through the config.json file.

### Dependencies

See requirements.txt and Dockerfiles.

### Links

* [Danish edits as seen through OSM Analytic Difference Engine](https://osm.expandable.dk)

* [Achavi diff viewer using overpass API](http://wiki.openstreetmap.org/wiki/Achavi)

* [Show Me The Way - a visual live service](http://osmlab.github.io/show-me-the-way/)

* [French OSM live service](http://live.openstreetmap.fr)
