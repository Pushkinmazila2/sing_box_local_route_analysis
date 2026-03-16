#!/usr/bin/env python3
"""
sing-box connection logger
Polls /connections API and logs in format:
Inbound/vless[tag] -> host:port -> Outbound/[chain] | Rule: ...
"""

import requests
import time
import json
import logging
import argparse
import os
from datetime import datetime

def setup_logger(log_file=None):
    fmt = "%(asctime)s %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"
    handlers = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    logging.basicConfig(level=logging.INFO, format=fmt, datefmt=datefmt, handlers=handlers)
    return logging.getLogger("singbox")

def parse_inbound(conn):
    """Extract inbound tag and protocol from metadata.type"""
    # type looks like: "vless/vless-13423" or "mixed/mixed-0"
    t = conn["metadata"].get("type", "unknown")
    parts = t.split("/")
    proto = parts[0] if parts else "unknown"
    tag = parts[1] if len(parts) > 1 else t
    return proto, tag

def parse_destination(conn):
    meta = conn["metadata"]
    host = meta.get("host") or meta.get("destinationIP") or "unknown"
    port = meta.get("destinationPort", "")
    return f"{host}:{port}" if port else host

def parse_outbound(conn):
    chains = conn.get("chains", [])
    if not chains:
        return "unknown"
    # chains[0] is the direct outbound, last is the final proxy
    return chains[0]

def parse_rule(conn):
    rule = conn.get("rule", "")
    # Shorten long rule_set rules
    if rule.startswith("rule_set="):
        # Extract route target
        if "=>" in rule:
            target = rule.split("=>")[-1].strip()
            return f"rule_set => {target}"
        return "rule_set"
    return rule or "final"

def format_connection(conn):
    proto, inbound_tag = parse_inbound(conn)
    dest = parse_destination(conn)
    outbound = parse_outbound(conn)
    rule = parse_rule(conn)
    network = conn["metadata"].get("network", "tcp").upper()
    src_ip = conn["metadata"].get("sourceIP", "")

    return (
        f"Inbound/{proto}[{inbound_tag}] "
        f"({src_ip}) "
        f"-> {dest} [{network}] "
        f"-> Outbound[{outbound}] "
        f"| Rule: {rule}"
    )

def poll_connections(api_url, secret, interval, log_file, seen_ttl=300):
    logger = setup_logger(log_file)
    headers = {"Authorization": f"Bearer {secret}"}
    url = f"{api_url}/connections"

    # Track seen connection IDs to log each connection only once
    seen = {}  # id -> timestamp first seen

    logger.info(f"Starting sing-box connection logger | API: {api_url} | Interval: {interval}s")

    while True:
        try:
            resp = requests.get(url, headers=headers, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            connections = data.get("connections", [])

            now = time.time()

            # Cleanup old seen entries
            seen = {k: v for k, v in seen.items() if now - v < seen_ttl}

            for conn in connections:
                cid = conn.get("id")
                if cid and cid not in seen:
                    seen[cid] = now
                    try:
                        line = format_connection(conn)
                        logger.info(line)
                    except Exception as e:
                        logger.warning(f"Failed to parse connection {cid}: {e}")

        except requests.exceptions.ConnectionError:
            logger.error(f"Cannot connect to API at {api_url}")
        except requests.exceptions.HTTPError as e:
            logger.error(f"API error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")

        time.sleep(interval)

def main():
    parser = argparse.ArgumentParser(description="sing-box connection logger")
    parser.add_argument("--api", default="http://127.0.0.1:9090", help="API base URL")
    parser.add_argument("--secret", default=os.environ.get("SINGBOX_SECRET", ""), help="API secret (or set SINGBOX_SECRET env)")
    parser.add_argument("--interval", type=float, default=2.0, help="Poll interval in seconds")
    parser.add_argument("--log-file", default=None, help="Log file path (optional, also logs to stdout)")
    args = parser.parse_args()

    if not args.secret:
        print("Error: --secret or SINGBOX_SECRET env required")
        exit(1)

    poll_connections(args.api, args.secret, args.interval, args.log_file)

if __name__ == "__main__":
    main()
