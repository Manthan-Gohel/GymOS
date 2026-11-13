from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.core import Branch, Gym
from app.models.member import Member
from app.models.membership import Membership
from app.models.plan import MembershipPlan
from app.models.trainer import Trainer, TrainerAvailability


@dataclass(frozen=True)
class PlanInfo:
    id: int
    name: str
    duration_days: int
    price_paise: int
    currency: str
    terms: dict | None
    is_active: bool


@dataclass(frozen=True)
class TrainerInfo:
    id: int
    full_name: str
    specialty: str | None
    bio: str | None
    availability: list[dict]


@dataclass(frozen=True)
class BranchInfo:
    id: int
    name: str
    address: str | None
    phone: str | None
    timings: str | None


@dataclass(frozen=True)
class GymKnowledge:
    gym_name: str
    branch: BranchInfo
    plans: list[PlanInfo]
    trainers: list[TrainerInfo]
    currency: str
    contact_phone: str | None
    contact_email: str | None


def get_gym_knowledge(db: Session, *, gym_id: int, branch_id: int) -> GymKnowledge:
    """Fetch all structured data needed to ground chatbot answers for a gym/branch."""
    gym = db.query(Gym).filter(Gym.gym_id == gym_id).first()
    branch = db.query(Branch).filter(Branch.id == branch_id, Branch.gym_id == gym_id).first()

    plans = db.query(MembershipPlan).filter(MembershipPlan.gym_id == gym_id, MembershipPlan.is_active.is_(True)).all()
    trainers = db.query(Trainer).filter(Trainer.gym_id == gym_id, Trainer.is_active.is_(True)).all()

    trainer_infos: list[TrainerInfo] = []
    for t in trainers:
        slots = db.query(TrainerAvailability).filter(TrainerAvailability.gym_id == gym_id, TrainerAvailability.trainer_id == t.id).all()
        trainer_infos.append(
            TrainerInfo(
                id=t.id,
                full_name=t.full_name,
                specialty=t.specialty,
                bio=t.bio,
                availability=[{"weekday": s.weekday, "start_time": s.start_time.strftime("%H:%M"), "end_time": s.end_time.strftime("%H:%M")} for s in slots],
            )
        )

    branch_info = BranchInfo(
        id=branch.id if branch else 0,
        name=branch.name if branch else "Main",
        address=None,  # not modeled yet
        phone=None,
        timings=None,  # not modeled yet
    )

    return GymKnowledge(
        gym_name=gym.name if gym else "Gym",
        branch=branch_info,
        plans=[
            PlanInfo(
                id=p.id,
                name=p.name,
                duration_days=p.duration_days,
                price_paise=p.price_paise,
                currency=p.currency,
                terms=p.terms,
                is_active=p.is_active,
            )
            for p in plans
        ],
        trainers=trainer_infos,
        currency=plans[0].currency if plans else "INR",
        contact_phone=None,
        contact_email=None,
    )


def format_knowledge_for_llm(knowledge: GymKnowledge) -> str:
    """Render structured knowledge as a concise text block for LLM system prompt."""
    lines = [
        f"Gym: {knowledge.gym_name}",
        f"Branch: {knowledge.branch.name}",
        f"Currency: {knowledge.currency}",
        "",
        "Active Plans:",
    ]
    for p in knowledge.plans:
        price = f"{p.price_paise / 100:,.0f} {p.currency}"
        duration = f"{p.duration_days} days"
        terms_str = ""
        if p.terms:
            if isinstance(p.terms, dict):
                terms_str = " - " + ", ".join(f"{k}: {v}" for k, v in p.terms.items())
            else:
                terms_str = f" - {p.terms}"
        lines.append(f"  - {p.name}: {price} for {duration}{terms_str}")

    lines.append("")
    lines.append("Trainers:")
    for t in knowledge.trainers:
        spec = f" ({t.specialty})" if t.specialty else ""
        avail = ", ".join(
            f"{['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][a['weekday']]} {a['start_time']}-{a['end_time']}"
            for a in t.availability
        ) if t.availability else "no schedule"
        lines.append(f"  - {t.full_name}{spec}: {avail}")
        if t.bio:
            lines.append(f"    Bio: {t.bio}")

    return "\n".join(lines)


def get_member_context(db: Session, *, gym_id: int, member_id: int) -> dict | None:
    """Fetch member-specific context (active membership, dues, etc.) for personalized answers."""
    member = db.query(Member).filter(Member.id == member_id, Member.gym_id == gym_id).first()
    if member is None:
        return None
    membership = (
        db.query(Membership)
        .filter(Membership.member_id == member_id, Membership.gym_id == gym_id, Membership.status == "active")
        .first()
    )
    plan = None
    if membership:
        plan = db.query(MembershipPlan).filter(MembershipPlan.id == membership.plan_id, MembershipPlan.gym_id == gym_id).first()
    return {
        "member_id": member.id,
        "full_name": member.full_name,
        "phone": member.phone,
        "whatsapp_consent": member.whatsapp_consent,
        "whatsapp_opt_out": member.whatsapp_opt_out,
        "active_membership": {
            "plan_name": plan.name if plan else None,
            "end_date": membership.end_date.isoformat() if membership else None,
            "status": membership.status if membership else None,
        } if membership else None,
    }


def format_member_context(ctx: dict | None) -> str:
    if not ctx:
        return "Member: not found"
    lines = [f"Member: {ctx['full_name']} ({ctx['phone']})"]
    if ctx.get("active_membership"):
        m = ctx["active_membership"]
        lines.append(f"  Plan: {m['plan_name']}, ends {m['end_date']}, status {m['status']}")
    else:
        lines.append("  No active membership")
    return "\n".join(lines)