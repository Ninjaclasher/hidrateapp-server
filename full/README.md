# Full Server

This Django server can be used as a drop-in replacement for the upstream server. You can use this server if you wish to be in control of all your data at all times.

The downside is this server requires quite a bit more technical skills. You will need to know how to set up and maintain a database.

**Note:** As all data is in your hands, no information is stripped from the requests. This means that device location and geolocation will be stored as-is. However, tracking information is not logged.

## Installation
```sh
$ pip3 install -r requirements.txt
```

Create a `local_settings.py` file in `hidrate/` to override any settings, such as the `SECRET_KEY`, `ALLOW_HOSTS`, and `DEBUG`. Also, ensure you set the database settings properly if you plan to use anything other than the default `sqlite`.

In addition, if you modified your mobile app to change any API key headers, you must override them for the server as well. The default ones are in `settings.py` as `HIDRATE_APPLICATION_ID_VALUE`, `HIDRATE_REST_API_KEY_VALUE`, and `HIDRATE_CLIENT_KEY_VALUE`.

Generate the schema for the database:
```sh
$ python3 manage.py migrate
```

## Usage
For a development server, you can use:
```sh
$ python3 manage.py runserver
```

For production, you may wish to use [uwsgi](https://uwsgi-docs.readthedocs.io/en/latest/).
