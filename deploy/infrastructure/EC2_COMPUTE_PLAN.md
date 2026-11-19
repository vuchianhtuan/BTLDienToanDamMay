# TV1: local Controller + a dedicated EC2 Compute

Decision from Cong Tuan, 30/10/2026: retain local VMware Controller/Compute 1,
prepare an independent EC2 Compute 2. Do not repurpose Truong's live all-in-one lab.
No EC2 has been launched and no cost has been incurred by these preparation steps.

## Verified versus pending

- Follow-up direct audit 30/10 at 11:51 UTC: Controller SSH available again;
  nova-compute up, both OVN agents alive, gateway service active, br-ex retains
  172.24.4.1/24 after boot. RAM available about 2.4 GiB inside the Ubuntu guest.
  No aggregate or second Compute. VPN query failed because Tailscale is absent.
  This follow-up supersedes the earlier timeout below; no VPN/EC2 has been added.
- Exact installed source revisions from that follow-up:
  DevStack `9b0a00865c2537338f72ed5b9b44a0d6bff16eb4`,
  Nova `94de0576ca02e0668233bedfbe7e18b87316c708`,
  Neutron `0d3e8e65b0c5171c654dcf2fca78bdd1b09b6107`,
  Placement `8e91e4d7aad1c6a642f80ec6387ce08d86f7c26d`,
  requirements `9edc04289eca1a4c18ae86e4430416d82a5b07fa`.
- Last direct local audit, 28/10: Ubuntu 24.04.5, DevStack master 9b0a0086,
  Nova KVM, OVN/Geneve, Controller and one local Compute up; no host aggregates.
- 30/10 SSH to 192.168.228.128 timed out. Current Controller availability and
  persistent gateway service after reboot have NOT been reverified.
- Local API/catalog, RabbitMQ and OVN refer to private VMware address
  192.168.228.128. An EC2 host cannot directly reach this address via the Internet.
- Prior local audit found no Tailscale binary. No VPN routing, ACL, MTU or
  cross-node service connectivity has been configured/tested.
- DevStack commit alone does NOT pin the entire installed OpenStack release.
  Must inventory actual Nova/Neutron/Placement/requirements source revisions too.
- AWS official documentation supports nested KVM on selected EC2 instance families;
  eligibility must be checked for the exact type in the chosen region at launch.
  A cheap/small EC2 is not automatically eligible.

## Before purchasing EC2

Choose region, exact type and a spending limit using live account availability/prices.
Do not select an instance on RAM alone. For KVM, the instance must support nested
virtualization, and the CPU option must be enabled. Do not silently fall back to
software QEMU emulation; if considered, document slow performance and agree separately.

Use Ubuntu Server 24.04 LTS x86_64 for initial compatibility. An initial capacity
proposal is 2 vCPU/4 GiB or more for Compute-only plus a small App VM, NOT a guaranteed
minimum or a verified purchasable SKU. Use the smallest eligible type actually offered,
then review total costs BEFORE launch: compute hours, EBS, public IPv4 and data transfer.
There is no extra nested-virtualization feature charge, but normal AWS costs still apply.
No promise of Free Tier eligibility is made.

With an authorized AWS CLI session, these are read-only discovery commands:

```bash
aws ec2 describe-instance-types --region REGION --filters Name=processor-info.supported-features,Values=nested-virtualization --query 'InstanceTypes[].{Type:InstanceType,vCPU:VCpuInfo.DefaultVCpus,MemoryMiB:MemoryInfo.SizeInMiB}'
aws ec2 describe-instance-type-offerings --region REGION --filters Name=instance-type,Values=EXACT_TYPE --location-type availability-zone
```

The operator must substitute REGION/EXACT_TYPE and inspect current console price.
This preparation does not use account credentials or grant authority to spend.
Use a separate SSH keypair/authorized public key, restricted inbound SSH from the
current operator address, encrypted root EBS, IMDSv2 and a descriptive project tag.
Do not expose RabbitMQ, MySQL, OVN databases or unrestricted Geneve to the Internet.

## Network design gate (must pass before running stack.sh)

Initial design: VPN between local Ubuntu and EC2 with a narrowly scoped route to
the existing Controller management address. Preserve current catalog endpoints
instead of changing every endpoint/DB binding while the lab is active.

Required verification:

1. Both nodes join an authorized VPN; advertise/approve only the Controller route
   needed (initially 192.168.228.128/32), and allow only the intended peers. This
   design must account for subnet-route SNAT and service binding addresses.
2. EC2 reaches Controller identity/compute/network/image/placement HTTP endpoints,
   RabbitMQ TCP 5672, OVN southbound TCP 6642 and any additional service actually
   required by the pinned DevStack compute configuration. Direct DB access is
   enabled only if the selected installer needs it, and only to that peer.
3. Geneve uses reachable VPN encapsulation addresses on BOTH OVN chassis,
   bidirectional UDP 6081, measured path MTU and a tenant MTU adjusted BEFORE test
   VM boot. Do not change Controller encap IP or tenant MTU without a recorded
   migration/rollback plan. Test old lab connectivity afterward.
4. VNC proxy-to-compute addresses/rules work over the private path if console is
   required. SSH tunnel to a single App port is NOT a cross-node network tunnel.
5. Clarify later TV3 Amphora routes/health-manager flows separately. This node
   connection alone does not deploy Octavia or shared TV2 data.

VPN enrollment/route approval and starting local Controller are pending. No
production/public firewall rules or VPN accounts were changed in this preparation.

## Version/installation gate

On Controller, run as stack, with this script copied to a known local path:

```bash
python3 audit_controller.py --output /opt/stack/tv1-controller-audit-NEW.json
```

All commands are fixed read-only queries, with timeouts and generic errors. The
script never prints openrc credentials, token, secret config or arbitrary stderr.
Output includes internal addresses; review before sharing. A failed VPN check is
expected until installation. Exit 0 only means queries succeeded, not that the
two-node deployment works.

Record exact source revisions and packages (including OVS/OVN). Prepare a private
compute local.conf from the DevStack multinode guide plus the matching installed
version, not from latest master blindly. Worker services include Nova compute,
Placement client, OVN controller/OVS and metadata agent; no duplicate Keystone,
Nova API or database on Compute 2. Cinder volume service is not necessary for a
compute-only node unless deliberately selected in the agreed storage design.

Secrets must be transferred privately with restricted permissions; do not paste
controller RabbitMQ/service passwords into chat or commit local.conf. Never run
the Controller's all-in-one local.conf unchanged on the new Compute.

## Acceptance and rollback

- Two distinct nova-compute hosts up and two Placement providers with inventory.
- Discover new cell host if needed; create separate aggregates/AZ-1 and AZ-2, each
  containing a distinct compute host. Existing VM stays untouched unless migration
  is planned. Do not claim two failure domains merely from AZ labels.
- Boot labelled synthetic VM on each AZ, verify actual scheduled host and network
  both directions, metadata and external access; save timestamped evidence.
- Keystone role/negative permission checks and SG negative checks are still required.
- Hand TV3 endpoints, subnet/network/SG IDs, AZs, capacity and evidence; hand TV2
  network requirements for shared Swift/DB, without moving its EC2 lab implicitly.
- On failure disable scheduling on ONLY the new node, retain logs, and remove only
  newly created test resources after review. Revert planned Controller encap changes
  if needed. Never delete existing lab volumes or rerun Controller stack.sh as a fix.

## Official references checked 30/10/2026

- AWS nested virtualization/type eligibility and enable option:
  https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/amazon-ec2-nested-virtualization.html
- DevStack multinode worker configuration:
  https://docs.openstack.org/devstack/latest/guides/multinode-lab.html
- DevStack configuration/version overrides:
  https://docs.openstack.org/devstack/latest/configuration.html

This is a PREPARATION PLAN, not a deploy-ready configuration. Controller access,
VPN, exact instance type/cost and source pinning are unresolved. No second Compute
or two-AZ connectivity has been verified.
