"""Helpers for building protocol specific link lists.

Kept dependency free so it can be imported (and tested) without touching the
Xray runtime or the network.
"""

from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple

#: Both spellings are accepted in the wild.
HYSTERIA2_SCHEMES: Tuple[str, ...] = ("hysteria2://", "hy2://")


def filter_links(links: Iterable[str], schemes: Sequence[str]) -> List[str]:
    """Keep only the links whose scheme is in ``schemes``, preserving order."""
    prefixes = tuple(scheme.lower() for scheme in schemes)
    return [link for link in links if link and link.strip().lower().startswith(prefixes)]
