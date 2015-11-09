FROM lunohq/services:latest

ADD dev-requirements.txt /app/dev-requirements.txt
ADD test-requirements.txt /app/test-requirements.txt
ADD bin/qt /usr/local/bin/qt
ADD bin/shell_plus /usr/local/bin/shell_plus
RUN pip install -r /app/dev-requirements.txt

ADD . /app
WORKDIR /app

CMD ["/bin/bash"]
