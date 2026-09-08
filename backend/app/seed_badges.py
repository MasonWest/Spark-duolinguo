"""Phase 9.2 Badge seed (idempotent).

Run from `database.init_db` (`seed_badges()`). Safe to call on existing DBs:
uses SQLite `INSERT ... ON CONFLICT(code) DO UPDATE` so re-running never
deletes rows (which would change rowid and break the
`user_badges.badge_id -> badge_definitions.id` FK -- the trap the user
flagged).

Naming policy
-------------
* 8 LEVEL badges come from `course_levels` (NOT hardcoded count). Future
  Level 8/9/... are auto-discovered at seed time.
* Names for the 8 existing Levels come from a hand-curated mapping (matches
  the text baked into `level<N..webp` artwork). For Levels added later,
  fallback to `course_levels.title`.
* 12 Special badges are hardcoded below -- they map 1:1 to the actual
  badge artwork already in `frontend/public/badges/`.
"""

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from .models import BadgeDefinition, CourseLevel

# Hand-curated Level Badge names (matches the text in level<N..webp).
# New Levels added without an entry here fall back to course_levels.title.
LEVEL_NAMES = {
    0: "Spark 引燃",
    1: "RDD 通关",
    2: "DataFrame 征服者",
    3: "SQL 解析师",
    4: "执行计划拆解者",
    5: "分区与 Shuffle 掌控者",
    6: "JOIN 炼金术师",
    7: "性能调优者",
}


SPECIAL_BADGES = [
    # code,            name,            description,                            image,                                     is_secret
    ("QUIZ_100",      "百题斩",          "累计答对 100 道题",                       "/badges/01_bai_ti_zhan.webp",      False),
    ("QUIZ_500",      "五百题斩",        "累计答对 500 道题",                       "/badges/02_wu_bai_ti_zhan.webp",   False),
    ("QUIZ_1000",     "千题帝",          "累计答对 1000 道题",                      "/badges/03_qian_ti_di.webp",       False),
    ("STREAK_7",      "7日修行",         "连续学习达到 7 天（历史最长）",            "/badges/04_7ri_xiuxing.webp",      False),
    ("STREAK_30",     "30日修行",        "连续学习达到 30 天（历史最长）",           "/badges/05_30ri_xiuxing.webp",     False),
    ("STREAK_100",    "100日修行",       "连续学习达到 100 天（历史最长）",          "/badges/06_100ri_xiuxing.webp",    False),
    ("REVIEW_50",     "复习狂人",        "累计通过 50 次间隔复习",                   "/badges/07_fuxi_kuangren.webp",    False),
    ("LATE_NIGHT",    "深夜代码者",      "在 00:00-05:00（本地时间）完成一次学习",    "/badges/08_shenye_daimazhe.webp",  True),
    ("WANMEI",        "完美通关",        "所有已掌握的课，最近一次测验都是 100%",      "/badges/09_wanmei_tongguan.webp",  False),
    ("BUG_HUNTER",    "Bug 猎手",        "debug 维度累计答对 20 道题",              "/badges/10_bug_lieshou.webp",      True),
    ("BLITZ",         "闪电战",          "一次测验 5/5 全对且用时不超过 60 秒",      "/badges/11_shandian_zhan.webp",    False),
    ("QUANJING",      "全景探索者",      "全部课程都已掌握",                         "/badges/12_quanjing_tansuozhe.webp", False),
]


def _upsert(db: Session, payload: dict) -> None:
    """INSERT ... ON CONFLICT(code) DO UPDATE -- preserves rowid."""
    stmt = sqlite_insert(BadgeDefinition).values(**payload)
    update_cols = {c: payload[c] for c in payload if c != "code"}
    stmt = stmt.on_conflict_do_update(
        index_elements=["code"],
        set_=update_cols,
    )
    db.execute(stmt)


def seed_badges(db: Session) -> dict:
    """Upsert all 20 Badge definitions. Returns counts for the caller's logs."""
    inserted_or_updated = 0

    # 1) Journey badges: one per existing course_level. The image filename
    #    matches the level's order_index; new levels fall back to title for
    #    both name AND image path, which will simply render as a missing
    #    image until artwork is provided -- acceptable for a non-MVP future.
    levels = db.scalars(select(CourseLevel).order_by(CourseLevel.order_index)).all()
    for level in levels:
        idx = level.order_index
        code = f"LEVEL_{idx}"
        name = LEVEL_NAMES.get(idx, level.title or code)
        payload = {
            "code": code,
            "name": name,
            "description": f"完成 Level {idx}（{name}）的全部课程",
            "tier": "journey",
            "image": f"/badges/level{idx}.webp",
            "sort_order": idx,
            "is_secret": False,
        }
        _upsert(db, payload)
        inserted_or_updated += 1

    # 2) Special badges: hardcoded list.
    for sort_offset, (code, name, desc, image, is_secret) in enumerate(SPECIAL_BADGES):
        payload = {
            "code": code,
            "name": name,
            "description": desc,
            "tier": "special",
            "image": image,
            "sort_order": 100 + sort_offset,
            "is_secret": is_secret,
        }
        _upsert(db, payload)
        inserted_or_updated += 1

    db.commit()
    return {"total_upserted": inserted_or_updated}