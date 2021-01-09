FROM python:alpine
WORKDIR /app
RUN \
    /sbin/apk add --no-cache python3 postgresql-libs && \
    /sbin/apk add --no-cache --virtual .build-deps gcc python3-dev musl-dev postgresql-dev libffi-dev
COPY ./requirements.txt /app/requirements.txt
RUN /usr/local/bin/pip install -r requirements.txt --no-cache-dir 
RUN /sbin/apk --purge del .build-deps
COPY ./ /app

CMD /usr/local/bin/python main.py
