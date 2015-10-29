FROM lunohq/services:latest

RUN apt-get update && apt-get install -y python-dev libncurses5-dev

ADD dev-requirements.txt /app/dev-requirements.txt
RUN pip install -r /app/dev-requirements.txt

ADD . /app
WORKDIR /app

CMD ["/bin/bash"]
