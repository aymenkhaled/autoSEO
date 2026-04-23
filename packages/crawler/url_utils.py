"""URL utilities — normalization, URL matching, and SSRF protection."""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

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
BLOCKED_HOST_SUFFIXES = (".local", ".internal", ".localhost")


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
    """Validate URL for SSRF safety using repeat DNS resolution."""
    try:
        parsed = urlparse(url)
    except Exception:
        return False

    if parsed.scheme not in ("http", "https"):
        return False
    if not parsed.hostname:
        return False
    if parsed.username or parsed.password:
        return False
    if parsed.hostname.lower().endswith(BLOCKED_HOST_SUFFIXES):
        return False

    # If hostname is itself an IP, check directly
    try:
        ip = ipaddress.ip_address(parsed.hostname)
        return not _is_blocked_ip(ip)
    except ValueError:
        pass  # Not an IP — resolve it

    ip_round_1 = _resolve_host_ips(parsed.hostname)
    ip_round_2 = _resolve_host_ips(parsed.hostname)
    if not ip_round_1 or not ip_round_2:
        return False

    for ip in ip_round_1 | ip_round_2:
        if _is_blocked_ip(ip):
            return False
    return True


def resolve_safe_url(url: str, base_url: str | None = None) -> str | None:
    """Resolve a possibly-relative URL and return it only if it is safe."""
    absolute = urljoin(base_url or "", url)
    return absolute if is_safe_url(absolute) else None


def urls_match_resource(public_url: str, candidate_url: str, site_domain: str | None = None) -> bool:
    """Best-effort equivalence check across absolute URLs, CMS paths, and relative paths."""
    public_parsed = urlparse(normalize_url(public_url))
    candidate_resolved = candidate_url

    if site_domain and candidate_url and not urlparse(candidate_url).netloc and candidate_url.startswith("/"):
        candidate_resolved = urljoin(site_domain if site_domain.endswith("/") else f"{site_domain}/", candidate_url.lstrip("/"))
    elif site_domain and candidate_url and not urlparse(candidate_url).scheme and not candidate_url.startswith("/"):
        candidate_resolved = urljoin(site_domain if site_domain.endswith("/") else f"{site_domain}/", candidate_url)

    candidate_parsed = urlparse(normalize_url(candidate_resolved))

    public_host = (public_parsed.hostname or "").lower()
    candidate_host = (candidate_parsed.hostname or "").lower()
    public_path = (public_parsed.path or "/").rstrip("/") or "/"
    candidate_path = (candidate_parsed.path or "/").rstrip("/") or "/"

    if public_path != candidate_path:
        return False
    if not candidate_host:
        return True
    return not public_host or public_host == candidate_host


def redirect_target_is_safe(base_url: str, redirect_target: str | None) -> bool:
    if not redirect_target:
        return True
    return resolve_safe_url(redirect_target, base_url=base_url) is not None


def _is_blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if (
        ip.is_loopback
        or ip.is_link_local
        or ip.is_private
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    ):
        return True
    return any(ip in net for net in BLOCKED_NETWORKS)


def _resolve_host_ips(hostname: str) -> set[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return set()

    resolved: set[ipaddress.IPv4Address | ipaddress.IPv6Address] = set()
    for info in infos:
        try:
            resolved.add(ipaddress.ip_address(info[4][0]))
        except ValueError:
            continue
    return resolved


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
