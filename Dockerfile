FROM ubuntu:14.04

# Update packages
RUN apt-get update -y

# Install Python Setuptools and Git
RUN apt-get install -y python-setuptools git

# Install pip
RUN easy_install pip

# Add deploy ssh key
ADD deploy/.ssh /root/.ssh
RUN chmod 400 /root/.ssh/id_rsa

# Add and install Python modules
ADD requirements.txt /src/requirements.txt
RUN cd /src; pip install --no-deps -r requirements.txt

ADD . /src

EXPOSE 5000

CMD ["python", "manage.py", "runserver", "0.0.0.0:5000"]
