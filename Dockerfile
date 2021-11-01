FROM python:alpine
COPY . .
RUN pip3 install --no-cache-dir -r /requirements.txt
ENTRYPOINT ["python3", "/hcclient"]
