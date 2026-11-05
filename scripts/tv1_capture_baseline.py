#!/usr/bin/env python3
"""Save a root-only pre-change baseline; never restores or changes networking."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import tarfile

if os.geteuid() != 0:
    raise SystemExit('Run with sudo on the intended OpenStack node')
os.umask(0o077)
stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
base = Path('/root/tv1-sg-baselines') / (socket.gethostname() + '-' + stamp)
base.mkdir(parents=True, mode=0o700)
commands = {
    'addresses': ['ip', '-br', 'addr'],
    'routes4': ['ip', '-4', 'route', 'show', 'table', 'all'],
    'routes6': ['ip', '-6', 'route', 'show', 'table', 'all'],
    'rules4': ['ip', '-4', 'rule'],
    'rules6': ['ip', '-6', 'rule'],
    'firewall4': ['iptables-save'],
    'firewall6': ['ip6tables-save'],
    'nft': ['nft', 'list', 'ruleset'],
    'ovs-external-ids': ['ovs-vsctl', '--format=json', 'list', 'Open_vSwitch'],
    'ovs-ports': ['ovs-vsctl', 'show'],
    'services': ['systemctl', 'list-units', '--type=service', '--all', '--no-pager'],
    'guests': ['virsh', 'list', '--all'],
    'ram': ['free', '-h'],
    'disk': ['df', '-h', '/'],
    'tailscale': ['tailscale', 'status'],
}
results = {}
for label, argv in commands.items():
    try:
        proc = subprocess.run(argv, capture_output=True, timeout=45)
        (base / (label + '.txt')).write_bytes(proc.stdout + proc.stderr)
        results[label] = proc.returncode
    except (OSError, subprocess.TimeoutExpired) as exc:
        results[label] = type(exc).__name__

# These files contain credentials. Keep this archive exclusively on the host.
roots = [Path('/etc/nova'), Path('/etc/neutron'), Path('/etc/netplan')]
files = []
for root in roots:
    if root.exists():
        files.extend(p for p in root.rglob('*') if p.is_file() and not p.is_symlink())
for pattern in ('devstack@*.service', 'tv1-*.service', 'devstack@*.service.d/*'):
    files.extend(p for p in Path('/etc/systemd/system').glob(pattern)
                 if p.is_file() and not p.is_symlink())
files.extend(p for p in Path('/usr/local/sbin').glob('tv1-*')
             if p.is_file() and not p.is_symlink())
files = sorted(set(files))
archive = base / 'config-private.tar.gz'
digests = {}
with tarfile.open(archive, 'w:gz') as tf:
    for path in files:
        digests[str(path).lstrip('/')] = hashlib.sha256(path.read_bytes()).hexdigest()
        tf.add(path, arcname=str(path).lstrip('/'), recursive=False)

# Validate archived bytes against the files that were read. This is NOT a
# database-consistent backup, restore drill, or permission to restore live state.
with tarfile.open(archive, 'r:gz') as tf:
    for name, expected in digests.items():
        data = tf.extractfile(name).read()
        if hashlib.sha256(data).hexdigest() != expected:
            raise SystemExit('Archive validation failed: ' + name)
manifest = {
    'utc': stamp, 'host': socket.gethostname(), 'commands': results,
    'file_sha256': digests,
    'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
    'archive_verified': True,
    'restore_drill_completed': False,
    'database_backup': False,
}
(base / 'manifest.json').write_text(json.dumps(manifest, indent=2))
print('BASELINE_DIRECTORY', base)
print('ARCHIVE_FILES', len(files))
print('ARCHIVE_BYTES_VERIFIED true')
print('RESTORE_DRILL_COMPLETED false')
print('OPTIONAL_COMMAND_FAILURES', json.dumps({k: v for k, v in results.items() if v != 0}))
