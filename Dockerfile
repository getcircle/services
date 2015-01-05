FROM ubuntu:14.04

# Update packages
RUN apt-get update -y

# Install dependencies
RUN apt-get install -y python-setuptools git python-dev libpq-dev

# Install pip
RUN easy_install pip

# Add deploy ssh key
ADD deploy/.ssh /root/.ssh
RUN chmod 400 /root/.ssh/id_rsa

RUN apt-get install -y libreadline6 libreadline6-dev

# Add and install Python modules
ADD requirements.txt /src/requirements.txt
RUN cd /src; pip install --no-deps -r requirements.txt

ADD . /src

EXPOSE 5000

CMD ["python", "manage.py", "runserver", "0.0.0.0:5000"]
