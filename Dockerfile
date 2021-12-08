FROM python:alpine

WORKDIR /app

RUN /sbin/apk add --no-cache python3
COPY ./requirements.txt /app/requirements.txt
RUN /usr/local/bin/pip3 install -r requirements.txt --no-cache-dir

COPY ./ /app

CMD /usr/local/bin/python3 main.py
