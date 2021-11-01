FROM python:alpine
COPY . .
RUN pip3 install -r /requirements.txt
ENTRYPOINT ["python3", "/hcclient"]
