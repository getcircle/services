FROM ubuntu:14.04

RUN echo LAST UPDATED 2015-01-28

# Update packages & Install Dependencies
RUN apt-get update -y && apt-get install -y python-setuptools git python-dev libpq-dev libffi-dev libssl-dev postgresql-client

# Install pip
RUN easy_install pip

# Install python requirements
ADD requirements.txt /opt/requirements.txt
RUN pip install --no-deps -r /opt/requirements.txt

EXPOSE 5000

ADD . /src
WORKDIR /src

RUN python manage.py collectstatic --noinput
CMD ["gunicorn", "services.wsgi", "-c", "services/gunicorn.py"]
