# mhahn/services-build
FROM mhahn/services-base:latest

RUN apt-get install -y \
    python-dev libffi-dev libssl-dev

ENV WHEELHOUSE=/wheelhouse
ENV PIP_WHEEL_DIR=/wheelhouse
ENV PIP_FIND_LINKS=/wheelhouse

VOLUME /wheelhouse
VOLUME /application

ENTRYPOINT pip wheel --no-deps -r /application/requirements.txt
