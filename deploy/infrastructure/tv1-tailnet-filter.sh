#!/bin/sh
# Controller is in a shared university tailnet. Restrict inbound OS traffic on
# tailscale0 to the explicitly enrolled Compute 2. SSH on ens33 is unaffected.
set -eu
peer=100.85.144.1/32
iptables -C INPUT -i tailscale0 -j DROP 2>/dev/null || iptables -I INPUT 1 -i tailscale0 -j DROP
iptables -C INPUT -i tailscale0 -s "$peer" -j ACCEPT 2>/dev/null || iptables -I INPUT 1 -i tailscale0 -s "$peer" -j ACCEPT
ip6tables -C INPUT -i tailscale0 -j DROP 2>/dev/null || ip6tables -I INPUT 1 -i tailscale0 -j DROP
