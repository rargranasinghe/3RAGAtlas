# Week 1 — Network Diagram
┌─────────────────┐         SSH (port 22)        ┌──────────────────────┐

│  Laptop (Host)   │  ───────────────────────────▶│  Debian 13 VM         │

│  Windows + PuTTY │      192.168.1.x (LAN)        │  hostname: debian-lab01│

│                  │ ◀───────────────────────────  │  IP: 192.168.1.213    │

└─────────────────┘                                │  Network: Bridged     │

└──────────────────────┘