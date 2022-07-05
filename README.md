# table_browser2

FinnGen coding variant result table server and frontend

## Running Docker image

Create a configuration file like [config.py](config.py) in your current directory.

Run container mapping port 8080 to host 8080 and mounting the current directory
to `/config` as config.py will be read from there.
Replace TAG with the current version. Depending on your `config.py` you may need
to give other `-v` mount volumes.

```
docker run -it -p 0.0.0.0:8080:8080/tcp -v `pwd`:/config eu.gcr.io/phewas-development/table_browser2:TAG
```

## Development

Requirements: Python 3.8+ and npm 8.3.1+ suggested

### Setup

Get code and install python libraries and node modules, e.g.:

```
git clone https://github.com/FINNGEN/table_browser2
cd table_browser2
pip3 install -r requirements.txt
npm ci
```

### Build JavaScript bundle

Build a JavaScript bundle from TypeScript sources to `static/bundle.js` in watch mode:

```
npx webpack --mode development --watch
```

Now you can modify frontend source code and a new bundle will be built automatically.

### Run server

Modify `config.py` to point to the data and run the server
(will run in port 8080 by default, reading config.py from the current directory):

```
server/run.py
```

### Build docker image

Replace IMAGE with your image name and TAG with your tag:

```
docker build -t IMAGE:TAG .
```
