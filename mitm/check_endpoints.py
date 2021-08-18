import json
import os
import urllib.parse

urls = []
for x in os.listdir('/tmp/logs/'):
    with open(os.path.join('/tmp/logs', x)) as f:
        v = json.loads(f.read())
    urls.append(v['path'].split('?')[0])
    if len(v['path'].split('?')) > 1:
        print(urllib.parse.unquote(v['path'].split('?')[1]))

print('\n'.join(set(urls)))
