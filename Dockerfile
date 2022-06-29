FROM ubuntu
RUN sudo apt-get update
RUN sudo apt-get install -y bash curl python3.6 pip
RUN sudo pip install --upgrade pip
RUN sudo pip install flask gunicorn requests datetime psycopg[binary]

RUN mkdir /app/
RUN mkdir /app/static/
RUN mkdir /app/templates

ADD static /app/static
ADD templates /app/templates

ADD *.py /app/
ADD codes.json /app/

WORKDIR /app/

EXPOSE 8080
EXPOSE 80
EXPOSE 443

CMD gunicorn --bind 0.0.0.0:8080 server:app