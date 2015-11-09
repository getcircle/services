FROM lunohq/services-base:latest

RUN apt-get update && apt-get install -y \
    xmlsec1 libevent-2.0 python-dev libncurses5-dev

ADD requirements.txt /app/requirements.txt
ADD wheelhouse /app/wheelhouse
RUN pip install --no-index -f /app/wheelhouse -r /app/requirements.txt

RUN git clone https://github.com/getcircle/heroku-buildpack-pgbouncer.git
RUN cd heroku-buildpack-pgbouncer && git checkout v0.4.0

ADD . /app
# cedar-14 refers to ubuntu-14.04 within the buildpack
RUN STACK='cedar-14' ./heroku-buildpack-pgbouncer/bin/compile /app

WORKDIR /app

EXPOSE 5000

CMD ["bin/start-pgbouncer-stunnel", "gunicorn", "services.wsgi", "-c", "services/gunicorn.py"]
