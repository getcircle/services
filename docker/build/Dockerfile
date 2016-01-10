FROM lunohq/services-base:latest

RUN apt-get update -y && apt-get install -y \
    python-dev libffi-dev libssl-dev xmlsec1 curl g++ libxml2-dev libxslt-dev
ENV WHEELHOUSE=/wheelhouse PIP_WHEEL_DIR=/wheelhouse PIP_FIND_LINKS=/wheelhouse
VOLUME /wheelhouse /application

ENTRYPOINT pip wheel --no-deps -r /application/requirements.txt
