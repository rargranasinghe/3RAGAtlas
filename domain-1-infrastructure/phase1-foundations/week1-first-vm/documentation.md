Week 1 — First Debian VM + SSH Access
## Objective
Create the first lab VM and establish SSH access from the host laptop, as the
foundation for all future Domain 1 labs.

## What was built
- A Debian 13 (trixie) virtual machine, created in VMware on a Windows laptop.
- Hostname: `debian-lab01`
- Networking: VMware Bridged mode, giving the VM a normal IP on the home LAN
  (DHCP-assigned, currently dynamic).
- Software: minimal install — SSH server and standard system utilities only
  (no desktop environment).
- SSH access confirmed from the host laptop using PuTTY.

## Why these choices
- **Bridged networking** was chosen over NAT so the VM behaves like a real
  device on the network — this will matter for future multi-VM labs
  (DNS, DHCP, Active Directory, etc.) where VMs need to communicate with
  each other and with the host directly.
- **Minimal install** (no GUI) mirrors how real servers are typically deployed
  — administered via SSH, not a desktop.
- **Dynamic IP** was kept for now; static IP configuration will be addressed
  properly during the Networking/DHCP phase rather than configured ad-hoc.
```