FROM lunohq/services-base:latest

RUN apt-get update -y && apt-get install -y \
    python-dev libffi-dev libssl-dev xmlsec1 curl autoconf build-essential libtool unzip

ADD bin/install-protobuf /tmp/install-protobuf
RUN /tmp/install-protobuf
ENV WHEELHOUSE=/wheelhouse PIP_WHEEL_DIR=/wheelhouse PIP_FIND_LINKS=/wheelhouse
VOLUME /wheelhouse /application

ENTRYPOINT cd /tmp/protobuf/python && python setup.py bdist_wheel -d /wheelhouse && pip wheel --no-deps -r /application/requirements.txt
