FROM docker.io/python:alpine
COPY . .
RUN pip3 install --no-cache-dir -r /requirements.txt
RUN apk add --no-cache ncurses
ENTRYPOINT ["python3", "/hcclient"]
