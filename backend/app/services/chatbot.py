from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.member import Member
from app.providers.llm import CannedFallbackLLMProvider, LLMProvider, get_llm_provider
from app.services.knowledge import (
    format_knowledge_for_llm,
    format_member_context,
    get_gym_knowledge,
    get_member_context,
)

HANDOFF_KEYWORDS = [
    "medical", "health", "injury", "pain", "doctor", "physio", "therapy",
    "refund", "money back", "cancel membership", "complaint", "unhappy", "angry",
    "legal", "lawyer", "court", "sue",
    "uncertain", "not sure", "don't know", "idk",
]

PLAN_KEYWORDS = ["plan", "price", "cost", "fee", "monthly", "quarterly", "annual", "package", "offer"]
TRAINER_KEYWORDS = ["trainer", "coach", "session", "class", "timing", "schedule", "availability"]
LOCATION_KEYWORDS = ["where", "location", "address", "branch", "near", "directions"]
TIMING_KEYWORDS = ["open", "close", "timing", "hours", "when", "time"]
MEMBERSHIP_KEYWORDS = ["membership", "renew", "freeze", "upgrade", "expir", "active"]


@dataclass(frozen=True)
class ChatbotDecision:
    reply: str
    handoff: bool
    reason: str | None = None
    meta: dict[str, Any] | None = None


def _should_handoff(text: str) -> tuple[bool, str | None]:
    lowered = text.lower()
    for kw in HANDOFF_KEYWORDS:
        if kw in lowered:
            return True, f"keyword: {kw}"
    return False, None


def _detect_intent(text: str) -> list[str]:
    lowered = text.lower()
    intents = []
    if any(kw in lowered for kw in PLAN_KEYWORDS):
        intents.append("plans")
    if any(kw in lowered for kw in TRAINER_KEYWORDS):
        intents.append("trainers")
    if any(kw in lowered for kw in LOCATION_KEYWORDS):
        intents.append("location")
    if any(kw in lowered for kw in TIMING_KEYWORDS):
        intents.append("timings")
    if any(kw in lowered for kw in MEMBERSHIP_KEYWORDS):
        intents.append("membership")
    return intents


def _canned_reply(intent: list[str], knowledge_text: str, member_ctx_text: str = "") -> str:
    if not intent:
        return "Thanks for your message! For specific queries about plans, trainers, timings, or your membership, please let me know. A staff member will follow up if needed."
    parts = ["Here's what I can share based on your query:"]
    if member_ctx_text:
        parts.append(member_ctx_text)
    if "plans" in intent:
        plans_section = knowledge_text.split("Active Plans:")[1].split("\n\n")[0] if "Active Plans:" in knowledge_text else ""
        parts.append(f"Plans:{plans_section}")
    if "trainers" in intent:
        trainers_section = knowledge_text.split("Trainers:")[1] if "Trainers:" in knowledge_text else ""
        parts.append(f"Trainers:{trainers_section[:500]}")
    if "location" in intent:
        lines = knowledge_text.split("\n")
        for line in lines:
            if "branch" in line.lower() or "address" in line.lower():
                parts.append(f"Location: {line.strip()}")
                break
    if "timings" in intent:
        parts.append("We're typically open 6 AM - 10 PM. For exact branch timings, please ask reception.")
    if "membership" in intent:
        parts.append("For membership-specific actions (renew, freeze, upgrade), please contact reception or share your registered phone number.")
    return "\n".join(parts)


def run_chatbot(
    db: Session,
    *,
    gym_id: int,
    branch_id: int,
    from_phone: str,
    inbound_text: str,
    conversation_id: int | None = None,
    llm: LLMProvider | None = None,
) -> ChatbotDecision:
    """Process an inbound message and return a grounded reply or handoff decision."""
    # 1. Check handoff keywords
    handoff, reason = _should_handoff(inbound_text)
    if handoff:
        return ChatbotDecision(
            reply="I've flagged this for a staff member to assist you directly. They'll reach out shortly.",
            handoff=True,
            reason=reason,
            meta={"trigger": "guardrail", "keyword": reason},
        )

    # 2. Load knowledge
    knowledge = get_gym_knowledge(db, gym_id=gym_id, branch_id=branch_id)
    knowledge_text = format_knowledge_for_llm(knowledge)

    # 3. Try member context (if conversation linked to member)
    member_ctx_text = ""
    if conversation_id:
        conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if conv:
            # Try to find member by phone
            member = db.query(Member).filter(Member.phone == from_phone, Member.gym_id == gym_id).first()
            if member:
                ctx = get_member_context(db, gym_id=gym_id, member_id=member.id)
                member_ctx_text = format_member_context(ctx)

    # 4. Detect intent for canned fallback
    intent = _detect_intent(inbound_text)

    # 5. Try LLM
    llm = llm or get_llm_provider()
    is_fallback_provider = isinstance(llm, CannedFallbackLLMProvider)
    system_prompt = (
        "You are a helpful gym assistant. Answer ONLY using the provided gym knowledge and member context. "
        "Never invent prices, promises, or policies. If unsure, say you'll have staff follow up. "
        "Keep replies concise (under 160 chars for WhatsApp)."
    )
    user_prompt = f"{knowledge_text}\n\n{member_ctx_text}\n\nMember asked: {inbound_text}"
    llm_handoff = False
    if not is_fallback_provider:
        try:
            result = llm.generate_reply(prompt=user_prompt, context={"system": system_prompt, "intent": intent})
            if result.get("ok") and not result.get("handoff"):
                return ChatbotDecision(
                    reply=str(result.get("reply", ""))[:500],
                    handoff=False,
                    meta={"provider": result.get("provider", "llm")},
                )
            llm_handoff = result.get("handoff", False)
        except Exception:
            pass

    # 6. Fallback to canned
    return ChatbotDecision(
        reply=_canned_reply(intent, knowledge_text, member_ctx_text),
        handoff=llm_handoff,
        reason="llm_unavailable_or_handoff" if not is_fallback_provider else "llm_disabled",
        meta={"provider": "canned", "intent": intent},
    )


def send_outbound_reply(
    db: Session,
    *,
    gym_id: int,
    branch_id: int,
    to_phone: str,
    body: str,
    conversation_id: int,
    provider_name: str = "chatbot",
) -> None:
    """Log an outbound bot reply to the conversation (audit trail)."""
    from app.models.message import OutboundMessage

    # Use the existing outbound logging (templates not required for bot replies)
    msg = OutboundMessage(
        gym_id=gym_id,
        branch_id=branch_id,
        member_id=None,
        phone=to_phone,
        template_name="chatbot_reply",
        body=body,
        kind="chatbot_reply",
        status="sent",
        provider=provider_name,
        who="chatbot",
        why=f"conversation:{conversation_id}",
    )
    db.add(msg)
    db.flush()