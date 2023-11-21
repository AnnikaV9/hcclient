FROM docker.io/python:alpine
COPY ./src /hcclient
RUN pip3 install --no-cache-dir -r /hcclient/requirements.txt
RUN apk add --no-cache ncurses
ENTRYPOINT ["python3", "/hcclient/hcclient"]
