# -*- coding: utf-8 -*-
# vim: tabstop=4 shiftwidth=4 expandtab
import sys
import socket
import argparse
import logging
from ipaddress import ip_address, IPv4Address
from dnslib import DNSRecord, DNSHeader, RR, A, QTYPE, DNSError, RCODE
from os import environ
from socketserver import ThreadingUDPServer, DatagramRequestHandler


logger = logging.getLogger("byosh")

allow_all = False
whitelist = set()
server_ip = None
debug_enabled = False


def domain_in_whitelist(domain: str, whitelist_entries: set) -> bool:
    domain = domain.rstrip(".")
    for entry in whitelist_entries:
        clean_entry = entry.lstrip(".")
        if domain == clean_entry or domain.endswith("." + clean_entry):
            return True
    return False


class PacketHandler(DatagramRequestHandler):
    def handle(self) -> None:
        data = self.rfile.read(512)
        if debug_enabled:
            logger.info("Request from %s", self.client_address[0])
        try:
            packet = DNSRecord.parse(data)
        except DNSError as err:
            logger.warning("Failed to parse DNS packet from %s: %s", self.client_address[0], err)
            reply = DNSRecord(
                DNSHeader(id=0, qr=1, aa=0, ra=1, rcode=RCODE.SERVFAIL)
            )
            self.wfile.write(reply.pack())
            return

        for question in packet.questions:
            requested_domain = question.get_qname()
            reply_packet = packet.reply()
            in_whitelist = allow_all or domain_in_whitelist(
                str(requested_domain), whitelist
            )
            if in_whitelist:
                reply_packet.add_answer(
                    RR(requested_domain, rdata=A(server_ip), ttl=60)
                )
                if debug_enabled:
                    logger.info(
                        "%s --> %s (proxied)", requested_domain.idna(), server_ip
                    )
            else:
                try:
                    real_ip = socket.gethostbyname(requested_domain.idna())
                except Exception as e:
                    if debug_enabled:
                        logger.warning(
                            "DNS resolution failed for %s: %s",
                            requested_domain.idna(),
                            e,
                        )
                    real_ip = server_ip
                reply_packet.add_answer(
                    RR(requested_domain, rdata=A(real_ip), ttl=60)
                )
                if debug_enabled:
                    logger.info(
                        "%s --> %s (direct)", requested_domain.idna(), real_ip
                    )
            self.wfile.write(reply_packet.pack())


def validate_ip(value: str) -> str:
    try:
        addr = ip_address(value)
        if not isinstance(addr, IPv4Address):
            raise ValueError(f"Only IPv4 addresses are supported, got: {value}")
        return value
    except ValueError as e:
        logger.error("Invalid IP address: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="byosh DNS server")
    parser.add_argument(
        "--ip",
        help="Public IP for proxied responses. Use ENV to read from PUB_IP env var",
        action="store",
        type=str,
        default="0.0.0.0",
    )
    parser.add_argument(
        "--whitelist",
        help="Path to whitelist domain file",
        action="store",
        type=str,
        default="Empty",
    )
    parser.add_argument(
        "--port", help="Listen port", action="store", type=int, default=53
    )
    parser.add_argument(
        "--debug", help="Enable debug logging", action="store_true"
    )
    args = parser.parse_args()

    debug_enabled = args.debug
    logging.basicConfig(
        level=logging.DEBUG if debug_enabled else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )

    raw_ip = args.ip
    if str(raw_ip).upper() == "ENV":
        raw_ip = environ.get("PUB_IP")
        if not raw_ip:
            logger.error(
                "PUB_IP environment variable is not set. "
                "Set it to your server's public IP address."
            )
            sys.exit(1)

    server_ip = validate_ip(raw_ip)

    logger.info("Starting byosh DNS server on 0.0.0.0:%d (PUB_IP=%s)", args.port, server_ip)

    if environ.get("DNS_ALLOW_ALL") == "YES" or args.whitelist == "ALL":
        allow_all = True
        logger.info("DNS_ALLOW_ALL enabled — proxying all domains")
    else:
        allow_all = False
        if args.whitelist not in ("Empty", ""):
            with open(args.whitelist) as f:
                for line in f:
                    stripped = line.strip()
                    if stripped:
                        whitelist.add(stripped)
            logger.info("Loaded %d entries from whitelist", len(whitelist))

    try:
        udp_sock = ThreadingUDPServer(("0.0.0.0", args.port), PacketHandler)
        logger.info("Listening on UDP 0.0.0.0:%d", args.port)
        udp_sock.serve_forever()
    except PermissionError:
        logger.error(
            "Permission denied — cannot bind to port %d. "
            "Run as root or use a port above 1024.",
            args.port,
        )
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Shutting down")
