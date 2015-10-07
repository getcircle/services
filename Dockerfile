FROM lunohq/services-base:latest

RUN apt-get install -y \
    postgresql-client xmlsec1 git curl

ADD . /app
RUN mkdir /app/bin

RUN git clone https://github.com/heroku/heroku-buildpack-pgbouncer.git
RUN STACK='cedar-14' ./heroku-buildpack-pgbouncer/bin/compile /app

WORKDIR /app

RUN pip install --no-index -f wheelhouse -r requirements.txt && \
    python manage.py collectstatic --noinput

EXPOSE 5000

CMD ["bin/start-pgbouncer-stunnel", "gunicorn", "services.wsgi", "-c", "services/gunicorn.py"]
