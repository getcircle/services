#!/bin/bash

./src/manage.py syncdb --noinput &> /var/log/syncdb.log
./src/manage.py migrate &> /var/log/migrate.log
