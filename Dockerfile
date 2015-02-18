FROM ubuntu:14.04

RUN echo LAST UPDATED 2015-01-28

# Update packages & Install Dependencies
RUN apt-get update -y && apt-get install -y python-setuptools git python-dev libpq-dev libffi-dev libssl-dev

# Install pip & curdling
RUN easy_install pip && pip install git+https://github.com/mhahn/curdling.git

# Install python requirements
ADD requirements.txt /opt/requirements.txt
RUN curd install -r /opt/requirements.txt

EXPOSE 5000

ADD . /src
WORKDIR /src

RUN python manage.py collectstatic --noinput
CMD ["gunicorn", "services.wsgi", "-c", "services/gunicorn.py"]
