#!/usr/bin/env python3
"""Run on the EC2 host as root. Uses real Swift, PostgreSQL and App VM."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import socket
import subprocess
import time
import uuid

import requests
from keystoneauth1 import session
from keystoneauth1.identity import v3
from swiftclient.client import Connection

args=argparse.ArgumentParser()
args.add_argument('--fault-tests',action='store_true',help='Temporarily stop this lab database to check dependency errors')
args.add_argument('--backup',action='store_true',help='Back up DB and Swift, restore DB into a temporary database, then remove that temporary DB')
options=args.parse_args()
root=Path('/srv/btl-tv2')
s=json.loads((root/'secrets.json').read_text()); state=json.loads((root/'state.json').read_text())
base=f"http://{state['app_ip']}:8000"
client=requests.Session(); client.headers['X-API-Key']=s['api_key']
auth=v3.ApplicationCredential(auth_url=state['auth_url'],application_credential_id=s['application_id'],application_credential_secret=s['application_secret'])
auth_session=session.Session(auth=auth)
swift=Connection(session=auth_session,os_options={'region_name':'RegionOne','endpoint_type':'internalURL'},timeout=15,retries=1)
ssh=['ssh','-n','-i',str(root/'id_ed25519'),'-o','BatchMode=yes','-o','UserKnownHostsFile='+str(root/'known_hosts'),'-o','ConnectTimeout=8']
checks=[]

def check(name,condition):
    if not condition: raise AssertionError(name)
    checks.append(name); print('PASS',name,flush=True)

def remote(command,binary=False,check_exit=True):
    p=subprocess.run([*ssh,'ubuntu@'+state['db_ip'],command],capture_output=True,text=not binary,timeout=90)
    if check_exit and p.returncode: raise RuntimeError(p.stderr if not binary else p.stderr.decode())
    return p.stdout

def api(method,path,**kwargs):
    return client.request(method,base+path,timeout=45,**kwargs)

def sql(query,database='integrity'):
    assert re.fullmatch(r'[a-z0-9_]+',database)
    encoded=query.replace("'","'\\''")
    return remote(f"sudo -n -u postgres psql -d {database} -Atc '{encoded}'").strip()

check('readiness',api('GET','/health/ready').status_code==200)
check('frontend and static assets',api('GET','/').status_code==200 and api('GET','/assets/app.js').status_code==200)
check('API key required',requests.get(base+'/api/files',timeout=10).status_code==401)
check('wrong API key denied',requests.get(base+'/api/files',headers={'X-API-Key':'incorrect'},timeout=10).status_code==401)
payload=b'TV2 real Swift and PostgreSQL integration\n'
r=api('POST','/api/files',params={'filename':'tv2-check-'+uuid.uuid4().hex[:8]+'.txt'},data=payload)
check('upload HTTP 201',r.status_code==201)
row=r.json(); ident=row['id']; assert str(uuid.UUID(ident))==ident
check('uploaded SHA-256',row['sha256']==hashlib.sha256(payload).hexdigest())
check('list includes file',any(x['id']==ident for x in api('GET','/api/files').json()))
check('download matches bytes',api('GET',f'/api/files/{ident}/download').content==payload)
check('verify intact',api('POST',f'/api/files/{ident}/verify').json()['intact'] is True)
_,stored=swift.get_object('file-integrity',ident)
check('object is stored in real Swift',stored==payload)
db_row=json.loads(sql(f"SELECT row_to_json(t) FROM (SELECT id,filename,size,sha256 FROM files WHERE id='{ident}') t"))
check('PostgreSQL metadata matches Swift object',db_row['sha256']==row['sha256'] and db_row['size']==len(payload))
check('PostgreSQL directory is on Cinder',sql('SHOW data_directory;')=='/srv/postgresql/data' and '/dev/vdb' in remote('findmnt -n -o SOURCE /srv/postgresql'))

try:
    changed=b'X'+payload[1:]
    swift.put_object('file-integrity',ident,contents=changed,content_length=len(changed))
    verified=api('POST',f'/api/files/{ident}/verify')
    check('same-size tampering detected',verified.status_code==200 and verified.json()['intact'] is False)
    swift.delete_object('file-integrity',ident)
    check('missing object returns 503 for verify',api('POST',f'/api/files/{ident}/verify').status_code==503)
    check('missing object returns 503 for download',api('GET',f'/api/files/{ident}/download').status_code==503)
finally:
    swift.put_object('file-integrity',ident,contents=payload,content_length=len(payload))
check('object restored after fault test',api('POST',f'/api/files/{ident}/verify').json()['intact'] is True)
check('25 MiB upload limit',api('POST','/api/files',params={'filename':'tv2-too-large.bin'},data=b'x'*(26214400+1)).status_code==413)
empty=api('POST','/api/files',params={'filename':'tv2-empty.txt'},data=b'')
check('empty file round trip',empty.status_code==201 and api('POST',f"/api/files/{empty.json()['id']}/verify").json()['intact'] is True)
one=api('POST','/api/files',params={'filename':'tv2-duplicate.txt'},data=b'one').json()
two=api('POST','/api/files',params={'filename':'tv2-duplicate.txt'},data=b'two').json()
check('duplicate names preserve separate objects',one['id']!=two['id'] and api('GET',f"/api/files/{one['id']}/download").content==b'one')
check('Swift unauthenticated access denied',requests.get(f"http://172.31.4.101:8080/v1/AUTH_{state['project_id']}/file-integrity",timeout=10).status_code==401)
check('Swift credential scoped to project',requests.get('http://172.31.4.101:8080/v1/AUTH_'+('0'*32)+'/file-integrity',headers={'X-Auth-Token':auth_session.get_token()},timeout=10).status_code==403)
try:
    sock=socket.create_connection((state['db_ip'],5432),timeout=3); sock.close(); accessible=True
except (TimeoutError,OSError): accessible=False
check('DB port blocked from host outside App security group',not accessible)

if options.fault_tests:
    try:
        remote('sudo -n systemctl stop postgresql@16-main.service')
        check('liveness stays 200 during database outage',api('GET','/health/live').status_code==200)
        check('readiness becomes 503 during database outage',api('GET','/health/ready').status_code==503)
        before={x['name'] for x in swift.get_container('file-integrity')[1]}
        failed=api('POST','/api/files',params={'filename':'tv2-db-outage.txt'},data=b'orphan compensation test')
        after={x['name'] for x in swift.get_container('file-integrity')[1]}
        check('failed metadata commit removes newly written object',failed.status_code==503 and before==after)
    finally:
        remote('sudo -n systemctl start postgresql@16-main.service')
    for attempt in range(20):
        if api('GET','/health/ready').status_code==200: break
        time.sleep(2)
    check('app recovers after database restart',api('GET','/health/ready').status_code==200 and api('POST',f'/api/files/{ident}/verify').json()['intact'] is True)

if options.backup:
    backup=root/'backups'/time.strftime('%Y%m%dT%H%M%SZ',time.gmtime()); backup.mkdir(parents=True,mode=0o700)
    dump=remote('sudo -n -u postgres pg_dump -Fc integrity',binary=True)
    (backup/'integrity.dump').write_bytes(dump); (backup/'integrity.dump').chmod(0o600)
    objects=backup/'swift'; objects.mkdir(mode=0o700)
    for item in swift.get_container('file-integrity')[1]:
        name=item['name']; assert str(uuid.UUID(name))==name
        _,body=swift.get_object('file-integrity',name)
        (objects/name).write_bytes(body); (objects/name).chmod(0o600)
    restore='integrity_restore_'+uuid.uuid4().hex[:8]
    try:
        remote('sudo -n -u postgres createdb '+restore)
        restore_ssh=[arg for arg in ssh if arg!='-n']
        proc=subprocess.run([*restore_ssh,'ubuntu@'+state['db_ip'],'sudo -n -u postgres pg_restore --no-owner --no-acl -d '+restore],input=dump,capture_output=True,timeout=90)
        if proc.returncode: raise RuntimeError(proc.stderr.decode())
        check('database backup restores into separate temporary DB',sql(f"SELECT sha256 FROM files WHERE id='{ident}'",database=restore)==row['sha256'])
    finally:
        remote('sudo -n -u postgres dropdb --if-exists '+restore)
    check('Swift objects backed up',len(list(objects.iterdir()))>0)
    print('Backup directory:',backup,flush=True)

report={'checked_at_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'checks':checks,'fixture_id':ident,'fixture_sha256':row['sha256'],'state':state}
path=root/'evidence'/'tv2-verification.json'; path.write_text(json.dumps(report,indent=2))
print(f'PASS {len(checks)} checks; report {path}',flush=True)
