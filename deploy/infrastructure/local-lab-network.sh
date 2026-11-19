#!/bin/sh
# Specific to Cong Tuan's existing VMware DevStack lab, not the TV2 EC2.
set -eu
ip link show br-ex >/dev/null
ip link show ens33 >/dev/null
ip link set br-ex up
ip address replace 172.24.4.1/24 dev br-ex
sysctl -w net.ipv4.ip_forward=1 >/dev/null
iptables -t nat -C POSTROUTING -s 172.24.4.0/24 -o ens33 -j MASQUERADE 2>/dev/null ||
    iptables -t nat -A POSTROUTING -s 172.24.4.0/24 -o ens33 -j MASQUERADE
iptables -C FORWARD -i br-ex -o ens33 -s 172.24.4.0/24 -j ACCEPT 2>/dev/null ||
    iptables -I FORWARD 1 -i br-ex -o ens33 -s 172.24.4.0/24 -j ACCEPT
iptables -C FORWARD -i ens33 -o br-ex -d 172.24.4.0/24 -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT 2>/dev/null ||
    iptables -I FORWARD 1 -i ens33 -o br-ex -d 172.24.4.0/24 -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
