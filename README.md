# Build Your Own Shecan

IMPORTANT NOTE: [sniproxy](https://github.com/mosajjal/sniproxy) is `byosh`'s eventual successor, which will offer a simpler architecture with better performance. Eventually byosh will be archived. 

`Shecan` is an anti-sanction service offered by a group of researchers in Iran. It allows you to use a different DNS server and have a transparent proxy for the whitelisted domains. 

Since Security and Privacy audits have no place in Iran, and `Shecan` obviously hasn't been through proper vetting, I decided to re-engineer something similar to it for personal use.

# Requirements

- Docker/podman(recommended)

# Proxied Domains

- Included in `domains` file inside the repository. "borrowed" from [fod](https://github.com/freedomofdevelopers/fod)

# How to Use

- make sure ports 80, 443 and 53 are not used in your system (disable `systemd-resolved` first: `systemctl disable --now systemd-resolved`)
- run the command in your server (remember to replace YOUR_PUBLIC_IP with you public facing IP address)

`docker run -d -p 53:53/udp -p 443:443 -p 80:80 --net=host -e PUB_IP=YOUR_PUBLIC_IP --name some-byosh mosajjal/byosh:latest`

# FAQ

## Why all these ports and also --net=host

Port 53 is used to recieve DNS and act as a DNS server. port 80 and 443 recieve HTTP traffic and handle the proxy side.

`--net=host` is needed because your Container engine will use NAT to push traffic to 443, and since your original IP will be masked from Nginx, it won't be able to handle proxy requests. 

## Can I have my own list

Sure! do the following

- clone the repo
- edit the domains file and add/remove your domains
- run `docker build . -t byosh:myown`
- run the command as before but from your own image tag:

`docker run -d -p 53:53/udp -p 443:443 -p 80:80 --net=host -e PUB_IP=YOUR_PUBLIC_IP --name some-byosh byosh:myown`

## Can I have this for ALL domains not just a list

run the following command (not tested):

`docker run -d -p 53:53/udp -p 443:443 -p 80:80 --net=host -e PUB_IP=YOUR_PUBLIC_IP -e DNS_ALLOW_ALL=YES --name some-byosh mosajjal/byosh:latest`

NOTE: you still have to provide a list file, albiet an empty one. It'll get ignored once the service is started

## How to verify the setup

After the container starts, test DNS resolution from a client configured to use the server's IP as its DNS server:

```bash
# A proxied domain should resolve to your server's IP
dig +short github.com @<SERVER_IP>

# A non-whitelisted domain should resolve to its real IP
dig +short example.com @<SERVER_IP>
```

HTTPS traffic to proxied domains will be transparently proxied through the server's nginx via SNI routing.

## Security and safety notes

- **byosh is an open DNS server.** Anyone with network access to UDP 53 on your server can use it as a DNS resolver. Use a firewall (e.g., `iptables`, `ufw`, cloud provider security groups) to restrict access to trusted clients.
- **`--net=host` exposes all ports** — the container shares the host network stack with no isolation. Only run on a dedicated server or VM.
- **The built-in whitelist uses suffix matching.** An entry like `.github.com` matches `api.github.com` and `github.com` but not `evilgithub.com` (domain-boundary enforced).
- **`DNS_ALLOW_ALL=YES` disables the whitelist entirely**, proxying all domains through the server. Use with caution and only when you understand the implications.
- **IPv6 is disabled** — the DNS server only processes IPv4 (A record) queries. AAAA queries receive no response.

## Limitation

This Project is at Alpha stage so expect weird behaviour! I've turned off `ipv6` everywhere so that's a known limitation. Other than that, the `dns.py` script is acting like a DNS server which is not a good practice for enterprise. Feel free to send PRs to make this better :)

