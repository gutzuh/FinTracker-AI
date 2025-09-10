from fastapi.testclient import TestClient
from api import webhook
import os

client = TestClient(webhook.app)

for path in ['/', '/api/webhook']:
    r = client.post(path, json={'update_id':1,'message':{'chat':{'id':999},'text':'teste'}})
    print(path, r.status_code, r.json())

print('last_update exists:', os.path.exists('last_update.json'))
if os.path.exists('last_update.json'):
    print('last_update size:', os.path.getsize('last_update.json'))
