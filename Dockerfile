FROM python:3.9-slim-buster

WORKDIR /broomstick

COPY . .
RUN pip3 install -r requirements.txt

CMD [ "python3", "main.py"]