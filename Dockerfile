FROM python:slim
RUN apt-get update
RUN apt-get install -yy --no-install-recommends git
RUN apt-get install -yy gcc make cmake
RUN pip install tox
