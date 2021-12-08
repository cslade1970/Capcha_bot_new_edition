FROM python:alpine

WORKDIR /app

COPY ./requirements.txt requirements.txt
RUN pip3 install -r requirements.txt --no-cache-dir

COPY ./ /app

CMD /usr/local/bin/python3 main.py
