"""Webhooks router — Stripe and GitHub webhook handlers."""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import stripe
import json

from dependencies import get_db
from config import get_settings
from models.tables import Organization

settings = get_settings()
router = APIRouter(tags=["webhooks"])


@router.post("/stripe")
async def handle_stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature"),
    db: AsyncSession = Depends(get_db),
):
    """Handle Stripe webhook events for subscription management."""
    if not stripe_signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe signature",
        )

    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            payload,
            stripe_signature,
            settings.STRIPE_WEBHOOK_SECRET,
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        # New subscription created
        customer_id = data.get("customer")
        subscription_id = data.get("subscription")
        
        if customer_id and subscription_id:
            await db.execute(
                update(Organization)
                .where(Organization.stripe_customer_id == customer_id)
                .values(
                    stripe_subscription_id=subscription_id,
                    plan="pro",  # Default to pro on first subscription
                )
            )
            await db.commit()

    elif event_type == "customer.subscription.updated":
        subscription_id = data.get("id")
        status_val = data.get("status")
        
        # Map Stripe status to plan
        plan_map = {"active": "pro", "past_due": "pro", "canceled": "starter"}
        new_plan = plan_map.get(status_val, "starter")

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
    x_github_event: str = Header(None, alias="x-github-event"),
    db: AsyncSession = Depends(get_db),
):
    """Handle GitHub webhook events (PR merged, etc.).
    
    TODO: Phase 5 — Implement:
    - pull_request.closed (merged) → mark issues as deployed
    - installation.created → store installation ID
    """
    body = await request.json()

    if x_github_event == "pull_request":
        action = body.get("action")
        if action == "closed" and body.get("pull_request", {}).get("merged"):
            # PR was merged — mark related issues as deployed
            pass  # Phase 5

    elif x_github_event == "installation":
        action = body.get("action")
        if action == "created":
            # New GitHub App installation
            pass  # Phase 5

    return {"status": "ok"}
