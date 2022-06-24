FROM ubuntu
RUN apt-get update && apt-get install -y bash curl python3.6 pip
RUN pip install --upgrade pip
RUN pip install flask gunicorn requests datetime flask-login psycopg[binary] bcrypt

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