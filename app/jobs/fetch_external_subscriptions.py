"""Background job to fetch external subscriptions."""

import base64
import logging
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

import requests

from app import logger, scheduler
from app.db import GetDB, subscription as subscription_store
from app.db.models import ExternalSubscription
from config import JOB_FETCH_EXTERNAL_SUBSCRIPTIONS_INTERVAL

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    TYPE_CHECKING = False


def parse_subscription_content(content: str) -> List[str]:
    """Parse subscription content and return a list of proxy links."""
    links = []
    
    # Try to decode as base64 first
    try:
        decoded = base64.b64decode(content).decode('utf-8')
        content = decoded
    except Exception:
        pass  # Not base64, use as-is
    
    # Split by lines and filter valid proxy links
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        # Check if it's a valid proxy link
        if any(line.startswith(scheme) for scheme in ['vless://', 'vmess://', 'trojan://', 'ss://', 'hysteria2://', 'hy2://', 'tuic://']):
            links.append(line)
    
    return links


def fetch_external_subscription(url: str, timeout: int = 30) -> Optional[str]:
    """Fetch external subscription content from URL."""
    try:
        headers = {
            'User-Agent': 'Marzban/0.8.4 (External Subscription Fetcher)',
            'Accept': 'text/plain,application/octet-stream,*/*',
        }
        response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch external subscription from {url}: {e}")
        return None


def fetch_single_external_subscription(db: "Session", sub: ExternalSubscription) -> dict:
    """Fetch a single external subscription and update its status."""
    logger.info(f"Fetching external subscription: {sub.name} ({sub.url})")
    
    content = fetch_external_subscription(sub.url)
    if content is None:
        sub.last_error = "Failed to fetch subscription"
        sub.last_fetched_at = datetime.utcnow()
        db.commit()
        return {"status": "error", "message": sub.last_error}
    
    links = parse_subscription_content(content)
    if not links:
        sub.last_error = "No valid proxy links found in subscription"
        sub.last_fetched_at = datetime.utcnow()
        db.commit()
        return {"status": "error", "message": sub.last_error}
    
    # Store the fetched links in the cache table
    stored_count = subscription_store.store_external_links(db, sub.id, links)
    
    sub.last_error = None
    sub.last_fetched_at = datetime.utcnow()
    db.commit()
    
    logger.info(f"Successfully fetched {stored_count} links from external subscription: {sub.name}")
    return {"status": "success", "links_count": stored_count}


def fetch_all_external_subscriptions():
    """Fetch all enabled external subscriptions."""
    logger.info("Starting scheduled fetch of external subscriptions")
    
    with GetDB() as db:
        subs = subscription_store.get_external_subscriptions(db, include_disabled=False)
        
        for sub in subs:
            try:
                fetch_single_external_subscription(db, sub)
            except Exception as e:
                logger.error(f"Error fetching external subscription {sub.name}: {e}")
                sub.last_error = str(e)
                sub.last_fetched_at = datetime.utcnow()
                db.commit()
    
    logger.info("Finished scheduled fetch of external subscriptions")


# Schedule the job - interval from config
scheduler.add_job(
    fetch_all_external_subscriptions,
    'interval',
    seconds=JOB_FETCH_EXTERNAL_SUBSCRIPTIONS_INTERVAL,
    coalesce=True,
    max_instances=1,
)