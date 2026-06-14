# Week 1 — Runbook: Build Debian VM + SSH Access

## Prerequisites
- VMware Workstation/Player installed on host
- Debian 13 netinst ISO downloaded

## Steps

1. Create a new VM in VMware:
   - 2 vCPUs, 2GB RAM, 20GB dynamically-allocated disk
   - Network adapter: Bridged
   - Attach the Debian 13 netinst ISO

2. Boot the VM and select **Graphical install**

3. Walk through the installer:
   - Language/locale/keyboard: set to preference
   - Hostname: `debian-lab01`, domain: blank
   - Set root password
   - Create non-root user account
   - Partitioning: Guided — use entire disk — all files in one partition
   - Software selection: keep **SSH server** and **standard system utilities**
     checked; uncheck all desktop environments (including GNOME, which is
     checked by default under "Debian desktop environment")
   - Install GRUB to the primary disk

4. Reboot. Log in at the console with the non-root user to confirm it boots
   correctly.

5. Find the VM's IP address:
   ip a