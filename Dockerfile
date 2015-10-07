FROM lunohq/services-base:latest

RUN apt-get install -y \
    postgresql-client xmlsec1 git curl libevent-2.0

ADD . /app
RUN mkdir /app/bin

RUN git clone https://github.com/getcircle/heroku-buildpack-pgbouncer.git
RUN cd heroku-buildpack-pgbouncer && git checkout v0.4.0
# cedar-14 refers to ubuntu-14.04 within the buildpack
RUN STACK='cedar-14' ./heroku-buildpack-pgbouncer/bin/compile /app

WORKDIR /app

RUN pip install --no-index -f wheelhouse -r requirements.txt && \
    python manage.py collectstatic --noinput

EXPOSE 5000

CMD ["bin/start-pgbouncer-stunnel", "gunicorn", "services.wsgi", "-c", "services/gunicorn.py"]
