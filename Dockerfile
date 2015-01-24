FROM ubuntu:14.04

ADD deploy/ssh /root/.ssh
RUN chmod 400 /root/.ssh/id_rsa
ADD deploy/scripts/setup.sh /deploy/scripts/setup.sh

RUN ./deploy/scripts/setup.sh

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
RUN pip install --no-deps git+ssh://git@github.com/django/django.git@e7b9a58b081299b30f807d5c66f7a5d1940efe4c
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

RUN pip install --no-deps git+ssh://git@github.com/getcircle/protobuf-to-dict.git@0.2.0
RUN pip install --no-deps git+ssh://git@github.com/getcircle/protobuf-soa.git@0.1.2
RUN pip install --no-deps git+ssh://git@github.com/getcircle/python-soa.git@0.6.12
RUN pip install --no-deps git+ssh://git@github.com/getcircle/django-common.git@0.2.2
RUN pip install --no-deps git+ssh://git@github.com/getcircle/protobuf-registry.git@0.27.2

EXPOSE 5000

ADD . /src
WORKDIR /src
CMD ["gunicorn", "services.wsgi", "-c", "services/gunicorn.py"]
