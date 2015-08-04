FROM mhahn/services-base

ADD . /src
WORKDIR /src

RUN pip install --no-index -f wheelhouse -r requirements.txt

EXPOSE 5000

RUN python manage.py collectstatic --noinput
CMD ["gunicorn", "services.wsgi", "-c", "services/gunicorn.py"]
