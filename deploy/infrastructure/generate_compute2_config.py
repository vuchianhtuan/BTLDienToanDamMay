"""Generate a private compute-only local.conf from an authenticated Controller shell.

Output contains credentials: pipe directly over verified SSH into a mode-600 file.
Do not run this interactively or store output in Git, logs or chat.
"""
import os
import shlex
import sys


def main():
    credentials = ("ADMIN_PASSWORD", "DATABASE_PASSWORD", "RABBIT_PASSWORD", "SERVICE_PASSWORD")
    if any(not os.environ.get(name) for name in credentials):
        print("Required credentials not available in Controller environment", file=sys.stderr)
        return 1
    values = {
        "HOST_IP": "100.85.144.1",
        "SERVICE_HOST": "192.168.228.128",
        "MYSQL_HOST": "192.168.228.128",
        "RABBIT_HOST": "192.168.228.128",
        "DATABASE_TYPE": "mysql",
        "ENABLED_SERVICES": "n-cpu,placement-client,ovn-controller,ovs-vswitchd,ovsdb-server,q-ovn-metadata-agent",
        "Q_AGENT": "ovn",
        "TUNNEL_IP": "100.85.144.1",
        "OVN_BUILD_FROM_SOURCE": "False",
        "NOVA_VNC_ENABLED": "True",
        "NOVNCPROXY_URL": "http://192.168.228.128:6080/vnc_lite.html",
        "VNCSERVER_LISTEN": "100.85.144.1",
        "VNCSERVER_PROXYCLIENT_ADDRESS": "100.85.144.1",
        "LOGFILE": "/opt/stack/logs/stack.sh.log",
        "NOVA_BRANCH": "94de0576ca02e0668233bedfbe7e18b87316c708",
        "NEUTRON_BRANCH": "0d3e8e65b0c5171c654dcf2fca78bdd1b09b6107",
        "PLACEMENT_BRANCH": "8e91e4d7aad1c6a642f80ec6387ce08d86f7c26d",
        "REQUIREMENTS_BRANCH": "9edc04289eca1a4c18ae86e4430416d82a5b07fa",
    }
    values.update({name: os.environ[name] for name in credentials})
    sys.stdout.write("[[local|localrc]]\n")
    for name, value in values.items():
        if "\n" in value or "\r" in value or "\x00" in value:
            print("Invalid configuration value", file=sys.stderr)
            return 1
        sys.stdout.write(f"{name}={shlex.quote(value)}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
