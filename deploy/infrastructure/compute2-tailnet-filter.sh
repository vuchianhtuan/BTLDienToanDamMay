#!/bin/sh
# EC2 Compute 2 is in a shared university tailnet. Permit inbound on tailscale0
# only from the enrolled Controller. SSH via the EC2 public interface is unaffected.
set -eu
peer=100.77.232.27/32
iptables -C INPUT -i tailscale0 -j DROP 2>/dev/null || iptables -I INPUT 1 -i tailscale0 -j DROP
iptables -C INPUT -i tailscale0 -s "$peer" -j ACCEPT 2>/dev/null || iptables -I INPUT 1 -i tailscale0 -s "$peer" -j ACCEPT
iptables -C INPUT -i tailscale0 -s 100.88.250.68/32 -j ACCEPT 2>/dev/null || iptables -I INPUT 1 -i tailscale0 -s 100.88.250.68/32 -j ACCEPT
ip6tables -C INPUT -i tailscale0 -j DROP 2>/dev/null || ip6tables -I INPUT 1 -i tailscale0 -j DROP
