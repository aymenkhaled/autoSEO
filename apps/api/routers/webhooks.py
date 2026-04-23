"""Webhook router — inbound Stripe/GitHub handlers plus outbound org webhooks."""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

import httpx
import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from dependencies import get_current_user, get_db
from models.tables import Organization, Webhook, WebhookDelivery
from packages.crawler.url_utils import is_safe_url, redirect_target_is_safe
from schemas.auth import AuthContext

settings = get_settings()
router = APIRouter(tags=["webhooks"])

_PROCESSED_EVENTS: dict[str, float] = {}
_REPLAY_TTL_SECONDS = 3600


class WebhookCreate(BaseModel):
    name: str
    url: str
    events: list[str] = Field(default_factory=list)
    enabled: bool = True


def _is_replayed(event_id: str | None) -> bool:
    if not event_id:
        return False
    now = time.time()
    expired = [key for key, seen_at in _PROCESSED_EVENTS.items() if now - seen_at > _REPLAY_TTL_SECONDS]
    for key in expired:
        _PROCESSED_EVENTS.pop(key, None)
    if event_id in _PROCESSED_EVENTS:
        return True
    _PROCESSED_EVENTS[event_id] = now
    return False


def _webhook_body(payload: dict) -> bytes:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _signature(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def _validate_webhook_url(url: str) -> None:
    if not is_safe_url(url):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook URL must be a public HTTP(S) endpoint",
        )


async def _deliver_webhook(db: AsyncSession, webhook: Webhook, event: str, payload: dict) -> WebhookDelivery:
    started = time.perf_counter()
    response_body = None
    status_code = None
    success = False
    body = _webhook_body(payload)

    headers = {
        "Content-Type": "application/json",
        "X-AutoSEO-Event": event,
        "X-AutoSEO-Signature": _signature(webhook.secret, body),
    }
    try:
        _validate_webhook_url(webhook.url)
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(webhook.url, content=body, headers=headers, follow_redirects=False)
            status_code = response.status_code
            location = response.headers.get("location")
            if response.is_redirect and not redirect_target_is_safe(webhook.url, location):
                response_body = "Unsafe webhook redirect target rejected"
            else:
                response_body = response.text[:1000]
                success = 200 <= response.status_code < 300
    except Exception as exc:
        response_body = str(exc)

    delivery = WebhookDelivery(
        webhook_id=webhook.id,
        org_id=webhook.org_id,
        event=event,
        payload=payload,
        status_code=status_code,
        response_body=response_body,
        duration_ms=int((time.perf_counter() - started) * 1000),
        success=success,
        attempted_at=datetime.now(timezone.utc),
    )
    db.add(delivery)
    await db.commit()
    await db.refresh(delivery)
    return delivery


@router.get("")
async def list_outbound_webhooks(
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(
            select(Webhook).where(Webhook.org_id == auth.org_id).order_by(Webhook.created_at.desc())
        )
    ).scalars().all()
    return {
        "webhooks": [
            {
                "id": str(webhook.id),
                "name": webhook.name,
                "url": webhook.url,
                "events": webhook.events,
                "enabled": webhook.enabled,
                "created_at": webhook.created_at.isoformat() if webhook.created_at else None,
            }
            for webhook in rows
        ],
        "total": len(rows),
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_outbound_webhook(
    data: WebhookCreate,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _validate_webhook_url(data.url)
    webhook = Webhook(
        org_id=auth.org_id,
        name=data.name,
        url=data.url,
        secret=f"whsec_{secrets.token_urlsafe(24)}",
        events=data.events,
        enabled=data.enabled,
        created_by=auth.user_id,
    )
    db.add(webhook)
    await db.commit()
    await db.refresh(webhook)
    return {
        "id": str(webhook.id),
        "name": webhook.name,
        "url": webhook.url,
        "events": webhook.events,
        "enabled": webhook.enabled,
        "secret": webhook.secret,
    }


@router.post("/{webhook_id}/test")
async def test_outbound_webhook(
    webhook_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    webhook = (
        await db.execute(select(Webhook).where(Webhook.id == webhook_id, Webhook.org_id == auth.org_id))
    ).scalar_one_or_none()
    if not webhook:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")

    payload = {
        "event": "webhook.test",
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "org_id": str(auth.org_id),
    }
    delivery = await _deliver_webhook(db, webhook, "webhook.test", payload)
    return {
        "delivery_id": str(delivery.id),
        "success": delivery.success,
        "status_code": delivery.status_code,
        "response_body": delivery.response_body,
    }


@router.get("/{webhook_id}/deliveries")
async def list_webhook_deliveries(
    webhook_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    webhook = (
        await db.execute(select(Webhook).where(Webhook.id == webhook_id, Webhook.org_id == auth.org_id))
    ).scalar_one_or_none()
    if not webhook:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")

    deliveries = (
        await db.execute(
            select(WebhookDelivery)
            .where(WebhookDelivery.webhook_id == webhook_id, WebhookDelivery.org_id == auth.org_id)
            .order_by(WebhookDelivery.attempted_at.desc())
            .limit(50)
        )
    ).scalars().all()
    return {
        "deliveries": [
            {
                "id": str(delivery.id),
                "event": delivery.event,
                "status_code": delivery.status_code,
                "response_body": delivery.response_body,
                "duration_ms": delivery.duration_ms,
                "success": delivery.success,
                "attempted_at": delivery.attempted_at.isoformat() if delivery.attempted_at else None,
            }
            for delivery in deliveries
        ]
    }


@router.post("/stripe")
async def handle_stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature"),
    db: AsyncSession = Depends(get_db),
):
    if not stripe_signature:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing Stripe signature")

    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(payload, stripe_signature, settings.STRIPE_WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature") from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if _is_replayed(event.get("id")):
        return {"status": "duplicate"}

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        customer_id = data.get("customer")
        subscription_id = data.get("subscription")
        if customer_id and subscription_id:
            await db.execute(
                update(Organization)
                .where(Organization.stripe_customer_id == customer_id)
                .values(stripe_subscription_id=subscription_id, plan="pro")
            )
            await db.commit()
    elif event_type == "customer.subscription.updated":
        subscription_id = data.get("id")
        status_value = data.get("status")
        new_plan = {"active": "pro", "past_due": "pro", "canceled": "starter"}.get(status_value, "starter")
        if subscription_id:
            await db.execute(
                update(Organization)
                .where(Organization.stripe_subscription_id == subscription_id)
                .values(plan=new_plan)
            )
            await db.commit()
    elif event_type == "customer.subscription.deleted":
        subscription_id = data.get("id")
        if subscription_id:
            await db.execute(
                update(Organization)
                .where(Organization.stripe_subscription_id == subscription_id)
                .values(plan="starter", stripe_subscription_id=None)
            )
            await db.commit()

    return {"status": "ok"}


@router.post("/github")
async def handle_github_webhook(
    request: Request,
    x_github_event: Optional[str] = Header(None, alias="x-github-event"),
    x_github_delivery: Optional[str] = Header(None, alias="x-github-delivery"),
    db: AsyncSession = Depends(get_db),
):
    if _is_replayed(x_github_delivery):
        return {"status": "duplicate"}

    body = await request.json()
    if x_github_event == "pull_request":
        action = body.get("action")
        if action == "closed" and body.get("pull_request", {}).get("merged"):
            pass
    elif x_github_event == "installation":
        action = body.get("action")
        if action == "created":
            pass
    return {"status": "ok"}
