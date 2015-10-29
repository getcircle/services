FROM lunohq/services-base:latest

RUN apt-get install -y \
    python-dev libffi-dev libssl-dev xmlsec1 curl automake build-essential libtool

ADD bin/install-protobuf /tmp/install-protobuf
RUN /tmp/install-protobuf
ENV WHEELHOUSE=/wheelhouse PIP_WHEEL_DIR=/wheelhouse PIP_FIND_LINKS=/wheelhouse
VOLUME /wheelhouse /application

ENTRYPOINT cd /tmp/protobuf-3.0.0-alpha-4/python && python setup.py bdist_wheel -d /wheelhouse && pip wheel --no-deps -r /application/requirements.txt
