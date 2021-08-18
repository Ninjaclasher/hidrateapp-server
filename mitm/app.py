import json
import os
import time
import urllib.parse

from flask import Flask, request

import requests


app = Flask(__name__)
app.config.from_object('config')
os.makedirs(app.config['LOG_PATH'])


@app.route('/', methods=app.config['HTTP_METHODS'])
def default():
    return 'success {}'.format(request.method)


def sanitize_headers(all_headers):
    headers = {}
    for key in (
        'X-Parse-Application-Id',
        'X-Parse-Rest-Api-Key',
        'X-Parse-App-Build-Version',
        'X-Parse-App-Display-Version',
        'X-Parse-Os-Version',
        'X-Parse-Installation-Id',
        'X-Parse-Client-Key',
        'X-Parse-Session-Token',
        'Content-Length',
        'Content-Type',
        'User-Agent',
    ):
        if key in all_headers:
            headers[key] = all_headers[key]

    return headers


def sanitize_data(all_data):
    if isinstance(all_data, str):
        return all_data
    elif isinstance(all_data, bytes):
        return all_data.decode()
    elif not all_data:
        return ''
    else:
        return json.dumps(all_data)


def call_api(headers=None, data=None):
    t = int(time.time() * 1000)

    if headers is None:
        headers = request.headers

    if data is None:
        data = request.data

    method = request.method
    headers = sanitize_headers(headers)
    data = sanitize_data(data)

    complete_path = request.path
    if request.args:
        complete_path += '?' + urllib.parse.urlencode(request.args)

    resp = getattr(requests, method.lower())(
        app.config['BASE_URL'] + complete_path,
        headers=headers,
        data=data,
    )

    if app.config['LOG_REQUESTS']:
        with open(os.path.join(app.config['LOG_PATH'], str(t)), 'w') as f:
            f.write(json.dumps({
                'method': method,
                'path': complete_path,
                'headers': headers,
                'data': json.loads(data) if data else '',
                'content': json.loads(resp.text),
                'code': resp.status_code,
            }, indent=4))

    return resp.text, resp.status_code


@app.route('/parse/classes/Bottle/<id>', methods=app.config['HTTP_METHODS'])
def classes_Bottle(id):
    try:
        data = json.loads(request.data)
    except json.decoder.JSONDecodeError:
        data = {}

    if isinstance(data.get('location'), dict):
        data['location']['latitude'] = 0
        data['location']['longitude'] = 0

    return call_api(data=data)


@app.route('/parse/classes/Day/<id>', methods=app.config['HTTP_METHODS'])
def classes_Day(id):
    try:
        data = json.loads(request.data)
    except json.decoder.JSONDecodeError:
        data = {}

    if isinstance(data, dict):
        data['altitude'] = 0
        data['isLocationUsed'] = False
        data['humidity'] = 0
        data['rank'] = 0
        if 'location' in data:
            del data['location']

    return call_api(data=data)


@app.route('/parse/config', methods=app.config['HTTP_METHODS'])
def config():
    content, code = call_api()

    try:
        content = json.loads(content)
    except json.decoder.JSONDecodeError:
        pass
    else:
        if isinstance(content.get('params'), dict):
            content['params'].update(**{
                'downloadAppUrl': False,
                'androidPregnancySettings': False,
                'trophyShareUrl': False,
                'trophySign': False,
                'hidePro': False,
            })
        content = json.dumps(content)

    return content, code


@app.route('/parse/classes/_Installation', methods=app.config['HTTP_METHODS'])
def classes_Installation_Main():
    try:
        data = json.loads(request.data)
    except json.decoder.JSONDecodeError:
        data = {}

    if isinstance(data, dict):
        data['deviceType'] = 'a'
        data['appVersion'] = 'a'
        data['deviceToken'] = 'a'

    return call_api(data=data)


@app.route('/parse/classes/_Installation/<id>', methods=app.config['HTTP_METHODS'])
def classes_Installation(id):
    try:
        data = json.loads(request.data)
    except json.decoder.JSONDecodeError:
        data = {}

    if isinstance(data, dict):
        data['deviceType'] = 'a'
        data['deviceName'] = 'a'
        data['deviceToken'] = 'a'

    return call_api(data=data)


@app.route('/parse/classes/Location', methods=app.config['HTTP_METHODS'])
def classes_Location():
    try:
        data = json.loads(request.data)
    except json.decoder.JSONDecodeError:
        data = {}

    if isinstance(data, dict):
        data['altitude'] = 0
        if isinstance(data.get('point'), dict):
            data['latitude'] = 0
            data['longitude'] = 0

    return call_api(data=data)


@app.route('/parse/<path:path>', methods=app.config['HTTP_METHODS'])
def parse(path):
    BLOCKED = (
        'functions/trophyanalytics',
        'events/AppOpened',
        'events/setManualGoal',
        'events/viewPreviousDay',
        'events/previousDay',
        'events/logout',
        'events/unpairBottle',
        'events/addBottle',
        'functions/getusergroups',
        'functions/getmychallenges',
        'functions/getmyawards',
        'functions/getmyfriends',
        'functions/getuserads',
        'functions/getjoinablechallenges',
        'functions/getclosedchallenges',
        'functions/getchallengedetail',
    )

    if path in BLOCKED:
        return json.dumps({'result': []}), 202

    return call_api()
