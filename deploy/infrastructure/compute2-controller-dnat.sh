#!/bin/sh
# EC2 only: preserve the Controller's existing catalog address over the VPN.
# Output DNAT is scoped to the single Controller IPv4 address; no subnet advertised.
set -eu
# Select the local Tailscale address as source before OUTPUT DNAT. Without this
# route the kernel chooses the EC2 private IP and Tailscale drops the packet.
ip -4 address show dev tailscale0 | grep -Fq '100.85.144.1/'
ip route replace 192.168.228.128/32 dev tailscale0 src 100.85.144.1
iptables -t nat -C OUTPUT -d 192.168.228.128/32 -j DNAT --to-destination 100.77.232.27 2>/dev/null ||
    iptables -t nat -I OUTPUT 1 -d 192.168.228.128/32 -j DNAT --to-destination 100.77.232.27
