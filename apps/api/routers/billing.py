import os

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth import require_auth
from database import get_db
from models import Billing, User

router = APIRouter(prefix="/api/billing", tags=["billing"])

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

PLAN_PRICE_IDS = {
    "basic_monthly": os.getenv("STRIPE_BASIC_MONTHLY_PRICE_ID", ""),
    "basic_yearly": os.getenv("STRIPE_BASIC_YEARLY_PRICE_ID", ""),
    "pro_monthly": os.getenv("STRIPE_PRO_MONTHLY_PRICE_ID", ""),
    "pro_yearly": os.getenv("STRIPE_PRO_YEARLY_PRICE_ID", ""),
}


def _get_stripe():
    try:
        import stripe
        stripe.api_key = STRIPE_SECRET_KEY
        return stripe
    except ImportError:
        raise HTTPException(status_code=503, detail="Payment service unavailable")


class CheckoutRequest(BaseModel):
    plan: str  # basic_monthly, basic_yearly, pro_monthly, pro_yearly


class CheckoutResponse(BaseModel):
    checkout_url: str


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    body: CheckoutRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    price_id = PLAN_PRICE_IDS.get(body.plan)
    if not price_id:
        raise HTTPException(status_code=400, detail="Invalid plan")

    stripe = _get_stripe()

    session = stripe.checkout.Session.create(
        mode="subscription",
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=os.getenv("FRONTEND_URL", "http://localhost:3000") + "/mypage?checkout=success",
        cancel_url=os.getenv("FRONTEND_URL", "http://localhost:3000") + "/pricing?checkout=cancel",
        client_reference_id=str(user.id),
        customer_email=user.email,
    )

    return CheckoutResponse(checkout_url=session.url)


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    stripe = _get_stripe()
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session.get("client_reference_id")
        if user_id:
            _activate_subscription(user_id, session, db)

    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        _cancel_subscription(subscription, db)

    return {"status": "ok"}


def _activate_subscription(user_id: str, session: dict, db: Session):
    plan_type = "basic"
    line_items = session.get("line_items", {}).get("data", [])
    for item in line_items:
        price_id = item.get("price", {}).get("id", "")
        if price_id in (PLAN_PRICE_IDS.get("pro_monthly"), PLAN_PRICE_IDS.get("pro_yearly")):
            plan_type = "pro"
            break

    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.plan_type = plan_type
        db.commit()

    billing = db.query(Billing).filter(Billing.user_id == user_id).first()
    if billing:
        billing.plan = plan_type
        billing.usage_count = 0
        db.commit()


def _cancel_subscription(subscription: dict, db: Session):
    customer_email = subscription.get("customer_email")
    if not customer_email:
        return

    user = db.query(User).filter(User.email == customer_email).first()
    if user:
        user.plan_type = "free"
        db.commit()

        billing = db.query(Billing).filter(Billing.user_id == user.id).first()
        if billing:
            billing.plan = "free"
            db.commit()


@router.get("/subscription")
async def get_subscription(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    billing = db.query(Billing).filter(Billing.user_id == user.id).first()
    return {
        "plan": billing.plan if billing else "free",
        "usage_count": billing.usage_count if billing else 0,
    }
