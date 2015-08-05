# mhahn/services-base
FROM ubuntu:14.04

# Update packages & Install Dependencies
RUN apt-get update -y && apt-get install -y \
    python-setuptools git libpq-dev && \
    easy_install pip==7.1.0 && pip install wheel
