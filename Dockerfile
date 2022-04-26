FROM nikolaik/python-nodejs:python3.10-nodejs18-slim
MAINTAINER Juha Karjalainen <jkarjala@broadinstitute.org>

WORKDIR /opt/browser
RUN npm install -D webpack-cli

COPY ./ ./

RUN pip3 install -r requirements.txt
RUN npx webpack --mode production

EXPOSE 8080

WORKDIR /config
CMD /opt/browser/server/run.py
