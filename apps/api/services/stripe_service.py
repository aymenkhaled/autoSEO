"""Stripe service — subscription management, customer creation, plan enforcement."""
import stripe
from config import get_settings

settings = get_settings()
stripe.api_key = settings.STRIPE_SECRET_KEY

# Plan limits
PLAN_LIMITS = {
    "starter": {
        "max_sites": 1,
        "max_pages_per_crawl": 100,
        "crawl_frequency": ["monthly"],
        "ai_fixes": False,
        "cms_integrations": False,
        "github_integration": False,
        "api_access": False,
    },
    "pro": {
        "max_sites": 10,
        "max_pages_per_crawl": 5000,
        "crawl_frequency": ["daily", "weekly", "biweekly", "monthly"],
        "ai_fixes": True,
        "cms_integrations": True,
        "github_integration": True,
        "api_access": True,
    },
    "agency": {
        "max_sites": 100,
        "max_pages_per_crawl": 50000,
        "crawl_frequency": ["daily", "weekly", "biweekly", "monthly"],
        "ai_fixes": True,
        "cms_integrations": True,
        "github_integration": True,
        "api_access": True,
    },
}


async def create_customer(email: str, name: str, org_id: str) -> str:
    """Create a Stripe customer for a new organization."""
    try:
        customer = stripe.Customer.create(
            email=email,
            name=name,
            metadata={"org_id": org_id},
        )
        return customer.id
    except stripe.error.StripeError:
        return ""


async def create_checkout_session(
    customer_id: str,
    price_id: str,
    success_url: str,
    cancel_url: str,
) -> str:
    """Create a Stripe Checkout session for subscription."""
    try:
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
        )
        return session.url
    except stripe.error.StripeError:
        return ""


async def create_portal_session(customer_id: str, return_url: str) -> str:
    """Create a Stripe Customer Portal session for managing subscription."""
    try:
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )
        return session.url
    except stripe.error.StripeError:
        return ""


def get_plan_limits(plan: str) -> dict:
    """Get the limits for a given plan."""
    return PLAN_LIMITS.get(plan, PLAN_LIMITS["starter"])


def can_add_site(plan: str, current_site_count: int) -> bool:
    """Check if the org can add another site."""
    limits = get_plan_limits(plan)
    return current_site_count < limits["max_sites"]


def can_crawl(plan: str, pages_requested: int) -> bool:
    """Check if the org can run a crawl with the requested page count."""
    limits = get_plan_limits(plan)
    return pages_requested <= limits["max_pages_per_crawl"]
