FROM ubuntu:26.04

RUN apt update
RUN apt install nodejs python3 -y
RUN apt install npm -y
RUN npm install -g @anthropic-ai/claude-code
RUN ln -s /app/ibtool_client.py /usr/bin/ibtool
RUN ln -s /app/ibtool_client.py /usr/bin/test.sh
WORKDIR /app
