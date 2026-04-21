"""URL utilities — normalization and SSRF protection.

Implements gap analysis fixes:
- Gap 1: URL normalization for deduplication
- Security 1: SSRF protection (block internal/loopback/link-local IPs)
"""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse, urlunparse, urlencode, parse_qsl

# Private/internal networks that must NEVER be crawled (SSRF protection)
BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),       # CGNAT
    ipaddress.ip_network("127.0.0.0/8"),         # loopback
    ipaddress.ip_network("169.254.0.0/16"),      # link-local (AWS/GCP metadata)
    ipaddress.ip_network("172.16.0.0/12"),       # private
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("192.168.0.0/16"),      # private
    ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),            # IPv6 unique local
    ipaddress.ip_network("fe80::/10"),           # IPv6 link-local
]

# Tracking parameters to strip during normalization
TRACKING_PARAM_PREFIXES = ("utm_", "_hs", "mc_", "vero_")
TRACKING_PARAM_NAMES = {
    "ref", "fbclid", "gclid", "msclkid", "yclid", "dclid", "twclid",
    "igshid", "trk", "_branch_match_id", "mkt_tok", "_ga",
}


def normalize_url(url: str) -> str:
    """Canonical form of a URL for deduplication.

    - Lowercase scheme and host
    - Remove fragment (#section)
    - Strip tracking query params (utm_*, fbclid, gclid, ...)
    - Normalize trailing slash (always trim except root)
    - Sort remaining query params for stable ordering
    """
    if not url:
        return url
    try:
        parsed = urlparse(url.strip())
    except Exception:
        return url

    scheme = (parsed.scheme or "https").lower()
    netloc = parsed.netloc.lower()

    # Strip default ports
    if netloc.endswith(":80") and scheme == "http":
        netloc = netloc[:-3]
    elif netloc.endswith(":443") and scheme == "https":
        netloc = netloc[:-4]

    # Path: trim trailing slash unless it's root
    path = parsed.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")

    # Filter tracking params
    params = parse_qsl(parsed.query, keep_blank_values=False)
    clean = [
        (k, v) for k, v in params
        if k.lower() not in TRACKING_PARAM_NAMES
        and not any(k.lower().startswith(p) for p in TRACKING_PARAM_PREFIXES)
    ]
    clean.sort()
    query = urlencode(clean)

    return urlunparse((scheme, netloc, path, "", query, ""))


def is_safe_url(url: str) -> bool:
    """Validate URL for SSRF safety BEFORE crawling.

    Rejects:
    - Non-http(s) schemes
    - URLs that resolve to private/loopback/link-local IPs
    - URLs with no hostname
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return False

    if parsed.scheme not in ("http", "https"):
        return False
    if not parsed.hostname:
        return False

    # If hostname is itself an IP, check directly
    try:
        ip = ipaddress.ip_address(parsed.hostname)
        return not _is_blocked_ip(ip)
    except ValueError:
        pass  # Not an IP — resolve it

    # Resolve hostname → IPs and check all addresses
    try:
        infos = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror:
        # DNS failure — let the crawler hit it and fail naturally
        return True

    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
            if _is_blocked_ip(ip):
                return False
        except ValueError:
            continue
    return True


def _is_blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if ip.is_loopback or ip.is_link_local or ip.is_private or ip.is_multicast:
        return True
    return any(ip in net for net in BLOCKED_NETWORKS)


def dedupe_urls(urls: list[str]) -> list[str]:
    """Normalize and deduplicate a list of URLs, preserving order."""
    seen = set()
    out = []
    for u in urls:
        n = normalize_url(u)
        if n and n not in seen:
            seen.add(n)
            out.append(n)
    return out
