FROM python:alpine
WORKDIR /app
COPY ./requirements.txt /app/requirements.txt
RUN /usr/local/bin/pip install -r requirements.txt
COPY ./ /app

CMD /usr/local/bin/python main.py
