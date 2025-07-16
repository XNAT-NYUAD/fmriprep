FROM python:3.9-slim

LABEL maintainer="amr.shadid@nyu.edu"

RUN mkdir /temp_files
COPY license.txt /opt/fs

WORKDIR /app
COPY ./code .

RUN apt-get update && \
    apt-get install -y rsync openssh-client sshpass && \
    pip install --no-cache-dir -r requirements.txt


RUN mkdir -p /root/.ssh
RUN chmod 700 /root/.ssh
COPY ssh /root/.ssh/
RUN chmod 600 /root/.ssh/id_rsa
