FROM ubuntu:14.04

ADD deploy/ssh /root/.ssh
RUN chmod 400 /root/.ssh/id_rsa
ADD deploy/scripts /deploy/scripts

RUN ./deploy/scripts/setup.sh

# Install Third Party Requirements
ADD requirements/third-party.txt /src/requirements/third-party.txt
RUN pip install --no-deps -r /src/requirements/third-party.txt

# Install Core Requirements
ADD requirements/core.txt /src/requirements/core.txt
RUN pip install --no-deps -r /src/requirements/core.txt

EXPOSE 5000

ADD . /src
RUN ./src/deploy/scripts/setup_db.sh

CMD ["python", "/src/manage.py", "runserver", "0.0.0.0:5000"]
