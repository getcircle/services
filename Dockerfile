FROM lunohq/services-base:latest

RUN apt-get update && apt-get install -y \
    xmlsec1 libevent-2.0 python-dev libncurses5-dev

ADD wheel-requirements.txt /app/wheel-requirements.txt
ADD wheelhouse /app/wheelhouse
RUN pip install --no-index --no-deps -f /app/wheelhouse -r /app/wheel-requirements.txt

ADD . /app

WORKDIR /app

EXPOSE 5000

CMD ["gunicorn", "services.wsgi", "-c", "services/gunicorn.py"]
