FROM mhahn/services-base:latest

RUN apt-get install -y \
    postgresql-client xmlsec1

ADD . /src
WORKDIR /src

RUN pip install --no-index -f wheelhouse -r requirements.txt && \
    python manage.py collectstatic --noinput

EXPOSE 5000

CMD ["gunicorn", "services.wsgi", "-c", "services/gunicorn.py"]
