FROM python:alpine

WORKDIR /app

ENV CRYPTOGRAPHY_DONT_BUILD_RUST=1

COPY ./requirements.txt /app/requirements.txt
RUN \
    /sbin/apk add --no-cache python3 postgresql-libs && \
    /sbin/apk add --no-cache --virtual .build-deps gcc python3-dev musl-dev postgresql-dev libffi-dev && \
    /usr/local/bin/pip install -r requirements.txt --no-cache-dir && \
    /sbin/apk --purge del .build-deps

COPY ./ /app

CMD /usr/local/bin/python main.py
