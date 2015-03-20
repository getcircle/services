FROM ubuntu:14.04

RUN echo LAST UPDATED 2015-01-28

# Update packages & Install Dependencies
RUN apt-get update -y && apt-get install -y python-setuptools git python-dev libpq-dev libffi-dev libssl-dev postgresql-client

# Install pip & curdling
RUN easy_install pip && pip install 'pip-accel[s3]'

# Install python requirements
ADD requirements.txt /opt/requirements.txt
RUN AWS_ACCESS_KEY_ID=AKIAIID4TMKFW27S4J6A AWS_SECRET_ACCESS_KEY=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 PIP_ACCEL_S3_BUCKET=otterbots-pip pip-accel install --no-deps -r /opt/requirements.txt

EXPOSE 5000

ADD . /src
WORKDIR /src

RUN python manage.py collectstatic --noinput
CMD ["gunicorn", "services.wsgi", "-c", "services/gunicorn.py"]
