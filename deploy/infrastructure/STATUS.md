# TV1 local Controller audit - 28/10/2026

Owner: Dinh Kieu Cong Tuan. Roles are TV1 infrastructure, TV2 Truong application/data,
TV3 Vu Chi Anh Tuan elasticity. This audit concerns the LOCAL VMware lab, not TV2 EC2.

## Observed directly over SSH

- Windows laptop: 15.4 GiB physical RAM. HypervisorPresent=false. One running VMware VM;
  configured 8192 MiB RAM, 4 vCPU, nested virtualization enabled, VMware NAT.
- Windows available RAM observed around 1.7 GiB; C: around 65.7 GiB free.
- Ubuntu 24.04.5 LTS, hostname openstack, management 192.168.228.128/24.
- DevStack master commit 9b0a0086; Nova virt_type=kvm; /dev/kvm exists.
- Nova scheduler/conductors and single nova-compute up. One hypervisor openstack.
- Only compute AZ nova; no host aggregates. internal is not a second workload AZ.
- Neutron OVN; Geneve encapsulation, encap IP 192.168.228.128; OVN southbound TCP 6642.
- Keystone/Nova/Placement/Glance/Neutron/Cinder endpoints on management address.
- No Swift/Heat/Octavia/Aodh/Gnocchi entries in local catalog.
- Existing lab2 VM PC01 is SHUTOFF; its disks, metadata and state were not changed.
- Guest memory 7.7 GiB, around 2.3 GiB available; root 58 GiB free.

## Network repair

After reboot, br-ex was administratively down, without IPv4, and the previous lab
NAT/forward rules were absent. Restored external gateway 172.24.4.1/24 on br-ex,
forwarding and NAT scoped to 172.24.4.0/24 via ens33. No flushing or policy changes.
The service/script in this directory are ONLY for this existing local lab. Do not
apply to the TV2 EC2 or a different addressing plan. IP routing now resolves external
lab addresses directly via br-ex. This does not by itself prove VM connectivity.

## Remaining TV1 work / capacity gate

The requested design is to continue on this laptop. A second independent Compute
VM has NOT been created: Windows available RAM is below a 4-GiB proposed compute
allocation, before VMware overhead. Do not pretend that naming two AZs on the single
Compute produces two compute nodes or failure isolation. Two VMware nodes on the same
laptop would be a multi-node lab but still have one physical failure domain.

Next: establish sufficient host memory for a second node; prepare a clean compute
VM on VMware NAT, with compatible Ubuntu/DevStack/plugin commits. Preserve the current
Controller and old lab. Register the second Nova/Placement/OVN node, discover its cell
host, then assign distinct hosts to AZ-1/AZ-2 and boot synthetic VMs to verify cross-node
network and external connectivity. Do not repurpose the TV2 EC2 without coordination.

Existing services bind management address 192.168.228.128. Local VMware nodes can use
the same NAT management network. Tailscale is not installed and is only needed if nodes
or operator access cross networks; VPN/routing/MTU must be tested if using remote nodes.

Security group/Keystone positive and negative access tests, team endpoint/runbook
handoff, two-compute/two-AZ evidence and integration with TV2/TV3 remain incomplete.
No new paid cloud resources, VM boot, AZ reassignment or controller reinstallation
was performed during this audit. Do not infer completion of TV1 from this document.
