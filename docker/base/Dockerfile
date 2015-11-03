# mhahn/services-base
FROM ubuntu:14.04

# add postgresql apt keys
RUN apt-get install -y curl && \
    curl https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add -
ADD etc/apt/sources.list.d/pgdg.list /etc/apt/sources.list.d/pgdg.list

# Update packages & Install Dependencies
RUN apt-get update -y && apt-get install -y \
    python-setuptools git libpq-dev postgresql-client-9.4 && \
    easy_install pip==7.1.0 && pip install wheel

ADD .bash_aliases /root/.bash_aliases
