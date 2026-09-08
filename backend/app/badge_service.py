"""Badge Engine (Phase 9.2).

Centralized rule registry + evaluator. The ONLY module that decides whether a
badge unlocks. Routers (quizzes.py / review.py) finish writing facts, call
`increment_user_stats(...)`, then call `evaluate_badges(...)` in the SAME
transaction.

Rules
-----
* No new "learning state" columns on lesson_mastery / course_levels. Every
  rule reads from existing tables (`lesson_mastery`, `course_levels`,
  `study_days`) plus the lifetime counters in `user_stats`.
* 20 badges, full re-evaluation per call is fine ("20 个 Badge 全量检查也完
  全可以接受"). Correctness > micro-optimization.
* `evaluate_badges` is idempotent: `UNIQUE(user_id, badge_id)` plus a same-
  transaction `INSERT OR IGNORE` makes double-evaluation a no-op.
* `is_secret` badges whose name/description/image are blanked in API
  responses when locked are still evaluated normally -- this is a presentation
  rule in `routers/badges.py`, not a rule-engine concern.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Dict, List, Optional

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from .models import (
    DEFAULT_USER_ID,
    BadgeDefinition,
    CourseLevel,
    Lesson,
    LessonMastery,
    StudyDay,
    UserBadge,
    UserStats,
)
from .services import compute_streak, local_now


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


@dataclass
class BadgeContext:
    """All facts the rule registry needs to evaluate a badge, pre-aggregated.

    Built once per call to `evaluate_badges`. Anything that requires more than
    one DB query lives here so the rule functions stay pure and tiny.
    """

    user_id: str

    # user_stats
    total_quiz_correct: int = 0
    total_quiz_submitted: int = 0
    total_reviews_passed: int = 0
    total_reviews_submitted: int = 0
    total_debug_correct: int = 0

    # derived from existing tables
    mastered_count: int = 0
    total_lessons: int = 0
    all_mastered_perfect: bool = False  # every mastered lesson scored 100% most recently
    longest_streak: int = 0
    current_streak: int = 0

    # event-derived (quiz submission only)
    is_late_night: bool = False  # 00:00-04:59 local
    blitz_duration_seconds: Optional[float] = None  # 5/5 quiz completed within 60s

    # level mastery: order_index -> (mastered_count, total_count)
    levels: Dict[int, tuple] = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Rule registry
# ---------------------------------------------------------------------------
#
# Each rule_fn signature: (BadgeContext) -> bool
# Anything that needs a DB read beyond the pre-built context (currently:
# LEVEL_* badges) is handled by `_check_level_badge` below, dispatched by code
# prefix inside `evaluate_badges`.


def _rule_quiz_100(ctx): return ctx.total_quiz_correct >= 100
def _rule_quiz_500(ctx): return ctx.total_quiz_correct >= 500
def _rule_quiz_1000(ctx): return ctx.total_quiz_correct >= 1000


def _rule_streak_7(ctx): return ctx.longest_streak >= 7
def _rule_streak_30(ctx): return ctx.longest_streak >= 30
def _rule_streak_100(ctx): return ctx.longest_streak >= 100


def _rule_review_50(ctx): return ctx.total_reviews_passed >= 50
def _rule_bug_hunter(ctx): return ctx.total_debug_correct >= 20


def _rule_blitz(ctx): return (
    ctx.blitz_duration_seconds is not None
    and 0 < ctx.blitz_duration_seconds <= 60
)
def _rule_late_night(ctx): return ctx.is_late_night


def _rule_wanmei(ctx):
    return ctx.mastered_count > 0 and ctx.all_mastered_perfect


def _rule_quanjing(ctx):
    return (
        ctx.total_lessons > 0
        and ctx.mastered_count == ctx.total_lessons
    )


BADGE_RULES: Dict[str, Callable[[BadgeContext], bool]] = {
    "QUIZ_100": _rule_quiz_100,
    "QUIZ_500": _rule_quiz_500,
    "QUIZ_1000": _rule_quiz_1000,
    "STREAK_7": _rule_streak_7,
    "STREAK_30": _rule_streak_30,
    "STREAK_100": _rule_streak_100,
    "REVIEW_50": _rule_review_50,
    "BUG_HUNTER": _rule_bug_hunter,
    "BLITZ": _rule_blitz,
    "LATE_NIGHT": _rule_late_night,
    "WANMEI": _rule_wanmei,
    "QUANJING": _rule_quanjing,
    # LEVEL_<N> dispatched separately (needs DB lookup).
}


# ---------------------------------------------------------------------------
# Context builder
# ---------------------------------------------------------------------------


def _parse_started_at(raw: Optional[str], now: datetime) -> Optional[datetime]:
    """Defensive parse of a client-supplied ISO timestamp for the 闪电战 clock.

    Returns None on ANY anomaly (None, malformed, in the future, > 3h old).
    Defensive because: (1) client clock may be wrong; (2) a stale tab open
    since yesterday should not earn a "speed" badge; (3) Phase 9.2 explicitly
    says "异常/无法解析时不要判定闪电战".
    """
    if not raw:
        return None
    try:
        # Python 3.11+ fromisoformat handles trailing 'Z'.
        ts = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if ts.tzinfo is not None:
            # The client sends UTC (browser `new Date().toISOString()`), and
            # `build_context` measures the duration against `datetime.utcnow()`
            # -- also UTC. Normalize to a NAIVE UTC timestamp so the subtraction
            # is frame-consistent. Converting to LOCAL here would make the delta
            # wrong on any non-UTC machine (e.g. UTC+8) and BLITZ could never fire.
            ts = ts.astimezone(timezone.utc).replace(tzinfo=None)
    except (ValueError, AttributeError):
        return None
    if ts > now + timedelta(minutes=1):  # tiny skew tolerance
        return None
    if (now - ts) > timedelta(hours=3):
        return None
    return ts


def _load_levels(db: Session) -> Dict[int, tuple]:
    """order_index -> (mastered_count, total_count). Single SQL query."""
    rows = db.execute(
        select(
            CourseLevel.order_index,
            func.count(Lesson.id),
            func.coalesce(
                func.sum(
                    case(
                        (LessonMastery.status == "mastered", 1),
                        else_=0,
                    )
                ),
                0,
            ),
        )
        .select_from(CourseLevel)
        .join(Lesson, Lesson.level_id == CourseLevel.id)
        .outerjoin(LessonMastery, LessonMastery.lesson_id == Lesson.id)
        .group_by(CourseLevel.order_index)
    ).all()
    return {order_index: (int(mastered), int(total)) for order_index, total, mastered in rows}


def _all_mastered_perfect(db: Session) -> bool:
    """True iff every mastered lesson's most recent quiz was 100%."""
    bad = db.scalar(
        select(func.count(LessonMastery.lesson_id)).where(
            LessonMastery.status == "mastered",
            LessonMastery.total_count > 0,
            or_(
                LessonMastery.correct_count != LessonMastery.total_count,
            ),
        )
    )
    return (bad or 0) == 0


def build_context(
    db: Session,
    user_id: str,
    *,
    event_kind: Optional[str] = None,  # "quiz" | "review" | None (read-only check)
    score: Optional[int] = None,
    total: Optional[int] = None,
    correct: Optional[int] = None,
    started_at: Optional[str] = None,
    debug_correct_in_event: int = 0,
    now: Optional[datetime] = None,
) -> BadgeContext:
    """Aggregate every fact a badge rule could need.

    Called from `evaluate_badges` once per evaluation pass. Read-only --
    callers that want stats to update must run `increment_user_stats(...)`
    first (the router does both, in the same transaction).
    """
    now = now or datetime.utcnow()

    stats = db.get(UserStats, user_id)
    ctx = BadgeContext(user_id=user_id)
    if stats is not None:
        ctx.total_quiz_correct = stats.total_quiz_correct or 0
        ctx.total_quiz_submitted = stats.total_quiz_submitted or 0
        ctx.total_reviews_passed = stats.total_reviews_passed or 0
        ctx.total_reviews_submitted = stats.total_reviews_submitted or 0
        ctx.total_debug_correct = (stats.total_debug_correct or 0) + debug_correct_in_event

    ctx.total_lessons = db.scalar(select(func.count(Lesson.id))) or 0
    ctx.mastered_count = db.scalar(
        select(func.count(LessonMastery.lesson_id)).where(LessonMastery.status == "mastered")
    ) or 0
    ctx.all_mastered_perfect = _all_mastered_perfect(db)

    streak = compute_streak(db, now=now)
    ctx.current_streak = streak.current
    ctx.longest_streak = streak.longest

    ctx.levels = _load_levels(db)

    # Event-derived facts. Both are only relevant for the submit that just
    # happened; the persisted counters above are the persistent side.
    # LATE_NIGHT is about the STUDY EVENT happening late, so it is only
    # meaningful for a real submit (quiz/review). Read-only checks and the
    # backfill path (event_kind=None) must NOT unlock it -- otherwise a
    # migration that happens to run at 03:00 would wrongly award it despite
    # there being no real late-night study event to attribute it to.
    ctx.is_late_night = event_kind is not None and local_now(now).hour < 5  # 00:00-04:59 local

    if event_kind == "quiz" and score == 100 and total == correct:
        # 5/5 (or whatever perfect == total) within 60s -> 闪电战
        parsed = _parse_started_at(started_at, now)
        if parsed is not None:
            ctx.blitz_duration_seconds = (now - parsed).total_seconds()
    # Event-debug correct is already merged into total_debug_correct above
    # (ctx reads stats + delta), so BUG_HUNTER reflects this submission too.
    return ctx


# ---------------------------------------------------------------------------
# Counter increment helper
# ---------------------------------------------------------------------------


def _get_or_create_stats(db: Session, user_id: str) -> UserStats:
    row = db.get(UserStats, user_id)
    if row is None:
        row = UserStats(user_id=user_id)
        db.add(row)
        db.flush()
    return row


def increment_user_stats(
    db: Session,
    user_id: str,
    *,
    quiz_correct: int = 0,
    quiz_submitted: bool = False,
    review_passed: bool = False,
    review_submitted: bool = False,
    debug_correct: int = 0,
) -> UserStats:
    """Additively update lifetime counters.

    Must be called BEFORE `evaluate_badges(...)` and INSIDE the same
    transaction. Counters intentionally never decrement -- and we never
    deduplicate the originating submit; one accepted POST == one increment,
    matching the existing `lesson_mastery.attempts` / `review_count` semantics.
    """
    s = _get_or_create_stats(db, user_id)
    if quiz_correct:
        s.total_quiz_correct = (s.total_quiz_correct or 0) + quiz_correct
    if debug_correct:
        s.total_debug_correct = (s.total_debug_correct or 0) + debug_correct
    if quiz_submitted:
        s.total_quiz_submitted = (s.total_quiz_submitted or 0) + 1
    if review_submitted:
        s.total_reviews_submitted = (s.total_reviews_submitted or 0) + 1
    if review_passed:
        s.total_reviews_passed = (s.total_reviews_passed or 0) + 1
    db.flush()
    return s


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------


def _check_level_badge(db: Session, ctx: BadgeContext, code: str) -> bool:
    """Generic LEVEL_<N> rule: every lesson in that level mastered."""
    try:
        idx = int(code.split("_", 1)[1])
    except (IndexError, ValueError):
        return False
    pair = ctx.levels.get(idx)
    if not pair:
        return False
    mastered, total = pair
    return total > 0 and mastered == total


def _new_badge_dict(badge: BadgeDefinition, unlocked_at: datetime) -> dict:
    """Return the public projection of a freshly unlocked badge."""
    return {
        "code": badge.code,
        "name": badge.name,
        "description": badge.description,
        "image": badge.image,
        "unlocked_at": unlocked_at.isoformat(),
    }


def evaluate_badges(
    db: Session,
    user_id: str = DEFAULT_USER_ID,
    *,
    event_kind: Optional[str] = None,
    score: Optional[int] = None,
    total: Optional[int] = None,
    correct: Optional[int] = None,
    started_at: Optional[str] = None,
    debug_correct_in_event: int = 0,
    now: Optional[datetime] = None,
) -> List[dict]:
    """Re-evaluate every badge against current facts; unlock any that newly
    qualify. Returns the list of NEWLY unlocked badges (in id order).

    Does NOT commit -- the caller (router / backfill) commits with its own
    surrounding transaction.
    """
    ctx = build_context(
        db,
        user_id,
        event_kind=event_kind,
        score=score,
        total=total,
        correct=correct,
        started_at=started_at,
        debug_correct_in_event=debug_correct_in_event,
        now=now,
    )

    definitions = db.scalars(select(BadgeDefinition).order_by(BadgeDefinition.sort_order, BadgeDefinition.id)).all()
    if not definitions:
        return []

    already_unlocked_ids = set(
        db.scalars(
            select(UserBadge.badge_id).where(UserBadge.user_id == user_id)
        ).all()
    )

    newly: List[dict] = []
    now = now or datetime.utcnow()
    for badge in definitions:
        if badge.id in already_unlocked_ids:
            continue
        unlocked = False
        if badge.code.startswith("LEVEL_"):
            unlocked = _check_level_badge(db, ctx, badge.code)
        else:
            rule = BADGE_RULES.get(badge.code)
            if rule is not None:
                unlocked = rule(ctx)
        if not unlocked:
            continue
        # INSERT OR IGNORE: if a parallel call raced us to insert the same
        # row, the unique constraint silently absorbs the duplicate -- exactly
        # the safety net the user requested ("UNIQUE 唯一, 幂等").
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert
        stmt = (
            sqlite_insert(UserBadge)
            .values(user_id=user_id, badge_id=badge.id, unlocked_at=now)
            .on_conflict_do_nothing(index_elements=["user_id", "badge_id"])
        )
        result = db.execute(stmt)
        db.flush()
        if result.rowcount == 0:
            # Already unlocked by another caller; not "newly" from our view.
            already_unlocked_ids.add(badge.id)
            continue
        already_unlocked_ids.add(badge.id)
        newly.append(_new_badge_dict(badge, now))

    return newly