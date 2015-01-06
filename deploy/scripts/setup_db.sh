#!/bin/bash

python /src/manage.py syncdb --noinput &> /var/log/syncdb.log
python /src/manage.py migrate &> /var/log/migrate.log
