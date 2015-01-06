#!/bin/bash

# Update packages
apt-get update -y

# Install dependencies
apt-get install -y python-setuptools git python-dev libpq-dev libffi-dev libssl-dev postgresql-client

# Install pip
easy_install pip
