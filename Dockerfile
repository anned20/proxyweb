FROM python:3.10-alpine

LABEL maintainer="annedouwe@bouma.tech"

WORKDIR /app

COPY ./requirements.txt requirements.txt

RUN pip3 install -r requirements.txt

COPY . /app
RUN cp /app/misc/entry.sh /app/ && chmod +x /app/entry.sh

# Install MySQL client
RUN apk add --no-cache mysql-client

ENTRYPOINT [ "./entry.sh" ]
CMD [ "app.py" ]
