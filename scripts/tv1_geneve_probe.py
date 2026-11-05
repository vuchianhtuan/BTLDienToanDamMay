#!/usr/bin/env python3
"""Temporary standalone kernel Geneve probe; never attaches to OVS/br-int.

Use UDP 6082 because production OVN already owns 6081. This does not validate
OVN options, tenant DHCP, metadata, production port policy, or VM traffic.
"""
import argparse
import datetime
import ipaddress
import os
import signal
import subprocess
import time

p = argparse.ArgumentParser()
p.add_argument('--peer', required=True)
p.add_argument('--side', choices=['a', 'b'], required=True)
p.add_argument('--rounds', type=int, choices=range(1, 21), default=3)
args = p.parse_args()
peer = ipaddress.IPv4Address(args.peer)
if peer not in ipaddress.IPv4Network('100.64.0.0/10'):
    p.error('peer must be a Tailscale IPv4')
if os.geteuid() != 0:
    p.error('requires sudo on the intended host')

name = 'gnv-tv1-test'
local, remote = ('198.18.173.1', '198.18.173.2')
if args.side == 'b':
    local, remote = remote, local

def run(*argv, **kwargs):
    return subprocess.run(argv, text=True, capture_output=True, timeout=20, **kwargs)

def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='milliseconds')

if run('ip', 'link', 'show', name).returncode == 0:
    raise SystemExit('STOP: test interface already exists; inspect ownership first')
routes = run('ip', '-4', 'route', 'show', 'table', 'all', check=True).stdout
for line in routes.splitlines():
    first = line.split()[0] if line.split() else ''
    if first in ('default', 'local', 'broadcast', 'unreachable'):
        continue
    try:
        if ipaddress.ip_network(first, strict=False).overlaps(
                ipaddress.ip_network('198.18.173.0/30')):
            raise SystemExit('STOP: test CIDR overlaps an existing route')
    except ValueError:
        pass

def interrupted(signum, frame):
    raise SystemExit('Interrupted; cleaning up')

signal.signal(signal.SIGTERM, interrupted)
signal.signal(signal.SIGINT, interrupted)
created = False
passed = False
try:
    run('ip', 'link', 'add', name, 'type', 'geneve', 'id', '730017',
        'remote', str(peer), 'dstport', '6082', check=True)
    created = True
    run('ip', 'link', 'set', name, 'mtu', '1200', check=True)
    run('ip', 'addr', 'add', local + '/30', 'dev', name, check=True)
    run('ip', 'link', 'set', name, 'up', check=True)
    print('READY_UTC', utc(), name, local, 'peer', peer, 'UDP6082 MTU1200', flush=True)
    time.sleep(8)
    for attempt in range(args.rounds):
        started = utc()
        result = run('ping', '-I', name, '-c', '3', '-W', '2', '-M', 'do',
                     '-s', '1172', remote)
        print('ATTEMPT', attempt + 1, 'START_UTC', started,
              'END_UTC', utc(), 'EXIT', result.returncode,
              result.stdout, result.stderr, flush=True)
        passed = passed or result.returncode == 0
        time.sleep(4)
    # Allow the peer's final round to finish if SSH setup was staggered.
    time.sleep(12)
finally:
    if created:
        result = run('ip', 'link', 'delete', name)
        print('CLEANUP_UTC', utc(), 'CLEANUP_EXIT', result.returncode, flush=True)
        if result.returncode:
            raise SystemExit('Cleanup failed; inspect gnv-tv1-test before retry')
if not passed:
    raise SystemExit('No successful probe; do not treat this run as passed')
