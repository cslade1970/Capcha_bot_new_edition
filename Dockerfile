FROM python:alpine3.12

WORKDIR /app

ENV CRYPTOGRAPHY_DONT_BUILD_RUST=1

COPY ./requirements.txt /app/requirements.txt
RUN \
    /sbin/apk add --no-cache python3 && \
    /usr/local/bin/pip install -r requirements.txt --no-cache-dir

COPY ./ /app

CMD /usr/local/bin/python main.py
