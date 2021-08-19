# Man-In-The-Middle Server

This Flask server can be used to log and view requests to the upstream server. You can see what type of data is sent and remove any sensitive information as needed. Currently, device information, geolocation, and tracking information are stripped before being sent to upstream.

If you don't wish to set up the full server, this is a good alternative. Keep in mind that your drink data will still be stored on the official servers.

## Note
You will need to run this server with a residential IP, as upstream blocks all non-residential IPs. If you do not receive a `403 Forbidden` when visiting [https://www.hidrateapp.com](https://www.hidrateapp.com), then your IP will work.

At the time of writing, there exists an alternate domain that connects to the same database but doesn't seem to have the same blocks in place. You can try [https://www.hidratefrost.com/](https://www.hidratefrost.com/), though note that this isn't guaranteed to work in the future.

If both of the above are not options, you may want to go for the full server instead.

## Installation
```sh
$ pip3 install -r requirements.txt
```

## Usage

For a development server, you can use:
```sh
$ python3 wsgi.py
```

For production, you may wish to use [uwsgi](https://uwsgi-docs.readthedocs.io/en/latest/).
