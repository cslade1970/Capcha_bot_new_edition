FROM python:alpine3.12

WORKDIR /app

RUN rm -rf /usr/bin/lsb_release

COPY ./requirements.txt /app/requirements.txt
RUN \
    /sbin/apk add --no-cache python3 && \
    /usr/local/bin/pip install -r requirements.txt --no-cache-dir

COPY ./ /app

CMD /usr/local/bin/python main.py
