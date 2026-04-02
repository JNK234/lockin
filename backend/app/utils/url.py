# ABOUTME: URL parsing utilities for extracting domains from full URLs.
# ABOUTME: Used to group visits by site in the Neo4j knowledge graph.

from urllib.parse import urlparse


def extract_domain(url: str) -> str:
    """Extract the domain from a URL, stripping www. prefix."""
    parsed = urlparse(url)
    domain = parsed.netloc or parsed.path
    if domain.startswith("www."):
        domain = domain[4:]
    return domain.lower()
