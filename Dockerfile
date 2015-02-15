FROM ubuntu:14.04

RUN echo LAST UPDATED 2015-01-28

# Update packages & Install Dependencies
RUN apt-get update -y && apt-get install -y python-setuptools git python-dev libpq-dev libffi-dev libssl-dev

# Install pip
RUN easy_install pip

# Install python requirements

RUN pip install --no-deps bcrypt==1.1.0
RUN pip install --no-deps boto==2.35.1
RUN pip install --no-deps cffi==0.8.6
RUN pip install --no-deps django-extensions==1.4.8
RUN pip install --no-deps django-grappelli==2.6.3
RUN pip install --no-deps django-phonenumber-field==0.6
RUN pip install --no-deps djangorestframework==3.0.0
RUN pip install --no-deps factory-boy==2.4.1
RUN pip install --no-deps phonenumbers==7.0.1
RUN pip install --no-deps protobuf==2.6.1
RUN pip install --no-deps psycopg2==2.5.4
RUN pip install --no-deps pycparser==2.10
RUN pip install --no-deps six==1.8.0
RUN pip install --no-deps wsgiref==0.1.2
RUN pip install --no-deps Django==1.8a1
RUN pip install --no-deps arrow==0.4.4
RUN pip install --no-deps python-dateutil==2.4.0
RUN pip install --no-deps pyotp==1.4.1
RUN pip install --no-deps twilio==3.6.14
RUN pip install --no-deps httplib2==0.9
RUN pip install --no-deps requests==2.5.1
RUN pip install --no-deps itsdangerous==0.24
RUN pip install --no-deps gunicorn==19.1.1
RUN pip install --no-deps greenlet==0.4.5
RUN pip install --no-deps gevent==1.0.1
RUN pip install --no-deps whitenoise==1.0.6
RUN pip install --no-deps python-linkedin==4.1
RUN pip install --no-deps oauthlib==0.7.2
RUN pip install --no-deps requests-oauthlib==0.4.2
RUN pip install --no-deps cryptography==0.7.2
RUN pip install --no-deps enum34==1.0.4
RUN pip install --no-deps pyasn1==0.1.7
RUN pip install --no-deps oauth2client==1.4.6
RUN pip install --no-deps pyasn1_modules==0.0.5
RUN pip install --no-deps rsa==3.1.4
RUN pip install --no-deps pycrypto==2.6.1
RUN pip install --no-deps django-date-extensions==1.0.0


RUN pip install --no-deps git+https://c9b60542c1a793a1bcc0b1e95ce3ab3d2da148c4:x-oauth-basic@github.com/getcircle/django-common.git@0.2.7
RUN pip install --no-deps git+https://c9b60542c1a793a1bcc0b1e95ce3ab3d2da148c4:x-oauth-basic@github.com/getcircle/protobuf-soa.git@0.4.0
RUN pip install --no-deps git+https://c9b60542c1a793a1bcc0b1e95ce3ab3d2da148c4:x-oauth-basic@github.com/getcircle/protobuf-to-dict.git@0.2.0
RUN pip install --no-deps git+https://c9b60542c1a793a1bcc0b1e95ce3ab3d2da148c4:x-oauth-basic@github.com/getcircle/python-soa.git@0.9.6
RUN pip install --no-deps git+https://c9b60542c1a793a1bcc0b1e95ce3ab3d2da148c4:x-oauth-basic@github.com/getcircle/protobuf-registry.git@0.34.3

EXPOSE 5000

ADD . /src
WORKDIR /src

RUN python manage.py collectstatic --noinput
CMD ["gunicorn", "services.wsgi", "-c", "services/gunicorn.py"]
