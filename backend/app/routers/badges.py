"""Badge catalog API (Phase 9.2).

Endpoints:
    GET /api/badges  -> full catalog for the (single) local user, with live
                        unlock state. Secret badges that are NOT yet unlocked
                        expose only their code + is_secret flag; name /
                        description / image are blanked so the catalog can't
                        leak what a hidden badge is.

The catalog is the badge_definitions table (seeded by seed_badges). Unlock
state comes from user_badges. No badge is ever "computed" here -- the engine
in badge_service decides unlocks; this router only projects existing facts.
"""

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import DEFAULT_USER_ID, BadgeDefinition, UserBadge
from ..schemas import BadgeOut

router = APIRouter(prefix="/api")


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def build_badge_out(
    badge: BadgeDefinition,
    unlocked_ids: set,
    unlocked_at_map: dict,
) -> BadgeOut:
    """Project one catalog row, blanking secret badges that are still locked."""
    unlocked = badge.id in unlocked_ids
    # A secret badge only reveals itself once earned.
    secret_locked = badge.is_secret and not unlocked
    return BadgeOut(
        code=badge.code,
        name="" if secret_locked else badge.name,
        description="" if secret_locked else badge.description,
        image="" if secret_locked else badge.image,
        tier=badge.tier,
        sort_order=badge.sort_order,
        is_secret=badge.is_secret,
        unlocked=unlocked,
        unlocked_at=unlocked_at_map.get(badge.id),
    )


@router.get("/badges", response_model=List[BadgeOut])
def list_badges(db: Session = Depends(get_db)) -> List[BadgeOut]:
    """Full badge catalog with per-user unlock state.

    Order mirrors the seed (journey badges by level, then special badges), so
    the frontend can group by `tier` without re-sorting.
    """
    definitions = db.scalars(
        select(BadgeDefinition).order_by(BadgeDefinition.sort_order, BadgeDefinition.id)
    ).all()

    rows = db.execute(
        select(UserBadge.badge_id, UserBadge.unlocked_at).where(
            UserBadge.user_id == DEFAULT_USER_ID
        )
    ).all()
    unlocked_ids = {row[0] for row in rows}
    unlocked_at_map = {
        row[0]: (row[1].isoformat() if row[1] is not None else None) for row in rows
    }

    return [build_badge_out(b, unlocked_ids, unlocked_at_map) for b in definitions]
