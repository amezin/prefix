FROM python:slim
RUN apt-get update
RUN apt-get install -yy git build-essential cmake pkg-config
RUN pip install tox
