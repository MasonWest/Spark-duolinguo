"""Level 4 答案位置重排（2026-09-09）

背景：L4 90 道题的 correct_index 分布严重失衡（A38/B45/C6/D1），学员可凭位置猜答案。

规则（用户确认）：
- 只对「尚无 quiz_answer_log 作答记录」的题重排，已作答的题保持原位置不动
  （selected_index 是按当时呈现位置记录的，重排会让历史记录语义错位）
- 顺序敏感题（选项本身是 0/1/2/3 等序列，如 q427）不重排
- 每课 10 题，四个位置尽量均衡；不同课用不同目标分布（rotate），避免跨课同位置规律
- 重排方式：正确项与目标位置的选项「两两交换」，不做全量打乱，最小扰动
- 解析里若写死了选项字母，一律改成引用选项文本，避免重排后解析失效

用法：python rebalance_l4_answers_20260909.py [--apply]   # 默认 dry-run
"""

import json
import sqlite3
import sys
from collections import Counter

DB = "spark_quest.db"
LEVEL_ORDER_INDEX = 4

# 顺序敏感题：选项是天然序列，打乱会很怪
FROZEN_QID = {427}

# 每课目标分布（按课序 rotate，避免每课都是同一个位置最多）
BASE_TARGET = [2, 3, 2, 3]


def rotate(lst, k):
    k %= len(lst)
    return lst[k:] + lst[:k]


def main(apply: bool):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute(
        """select q.id, q.lesson_id, q.prompt, q.options, q.correct_index, q.explanation
           from quizzes q join lessons l on l.id = q.lesson_id
           where l.level_id = (select id from course_levels where order_index = ?)
           order by q.lesson_id, q.order_index""",
        (LEVEL_ORDER_INDEX,),
    )
    rows = cur.fetchall()

    cur.execute("select distinct question_id from quiz_answer_log")
    logged = {r[0] for r in cur.fetchall()}

    # 先修掉解析里写死的选项字母（改成引用文本），这样重排后解析依然成立
    fix_exp(cur, rows, apply)

    by_lesson = {}
    for qid, lid, prompt, opt_json, ci, exp in rows:
        by_lesson.setdefault(lid, []).append(
            {"qid": qid, "prompt": prompt, "opts": json.loads(opt_json), "ci": ci, "exp": exp}
        )

    lesson_ids = sorted(by_lesson)
    changes = []          # (qid, old_ci, new_ci)
    for k, lid in enumerate(lesson_ids):
        items = by_lesson[lid]
        target = rotate(BASE_TARGET, k)

        fixed = [it for it in items if it["qid"] in logged or it["qid"] in FROZEN_QID]
        movable = [it for it in items if it not in fixed]

        have = Counter(it["ci"] for it in fixed)
        need = {i: max(0, target[i] - have.get(i, 0)) for i in range(4)}

        # 修正总数：need 之和必须等于可重排题数
        diff = len(movable) - sum(need.values())
        while diff > 0:
            i = min(range(4), key=lambda x: need[x])
            need[i] += 1
            diff -= 1
        while diff < 0:
            i = max(range(4), key=lambda x: need[x])
            if need[i] > 0:
                need[i] -= 1
                diff += 1
            else:
                break

        plan = list(range(4))
        for it in movable:
            # 优先保持原位（若该位置还有配额），否则取配额最多的位置
            if need.get(it["ci"], 0) > 0:
                tgt = it["ci"]
            else:
                cand = [i for i in plan if need[i] > 0]
                if not cand:
                    tgt = it["ci"]
                else:
                    tgt = max(cand, key=lambda x: need[x])
            need[tgt] -= 1
            it["_tgt"] = tgt

        for it in movable:
            old, new = it["ci"], it["_tgt"]
            if old == new:
                continue
            it["opts"][old], it["opts"][new] = it["opts"][new], it["opts"][old]
            changes.append((it["qid"], old, new, it["prompt"]))
            if apply:
                cur.execute(
                    "update quizzes set options=?, correct_index=? where id=?",
                    (json.dumps(it["opts"], ensure_ascii=False), new, it["qid"]),
                )

        final = Counter(it["_tgt"] if "_tgt" in it else it["ci"] for it in items)
        print(
            f"lesson {lid}: fixed={len(fixed)} movable={len(movable)} "
            f"target={target} final={[final.get(i, 0) for i in range(4)]}"
        )

    if apply:
        conn.commit()
    conn.close()

    print()
    print(f"重排题数: {len(changes)}（共 {len(rows)} 题，有作答记录冻结 "
          f"{sum(1 for r in rows if r[0] in logged)} 题，顺序敏感冻结 {len(FROZEN_QID)} 题）")
    if not apply:
        print("dry-run，未写入。加 --apply 执行。")
    return changes


def fix_exp(cur, rows, apply):
    """把解析里写死的「选项 X」改成引用选项文本，避免重排后解析失效。"""
    import re

    for qid, lid, prompt, opt_json, ci, exp in rows:
        if not exp or not re.search(r"选项\s*[ABCD]", exp):
            continue
        opts = json.loads(opt_json)
        m = re.search(r"选项\s*([ABCD])", exp)
        idx = ord(m.group(1)) - 65
        quoted = opts[idx]
        if len(quoted) > 40:
            quoted = quoted[:40] + "…"
        new_exp = exp.replace(m.group(0), f"「{quoted}」")
        print(f"[解析去字母] q{qid}: 选项 {m.group(1)} -> 「{quoted}」")
        if apply:
            cur.execute("update quizzes set explanation=? where id=?", (new_exp, qid))
    if apply:
        conn_commit = None


if __name__ == "__main__":
    do_apply = "--apply" in sys.argv
    if do_apply:
        import shutil

        shutil.copy(DB, DB + ".bak_before_rebalance_20260909")
        print("已备份:", DB + ".bak_before_rebalance_20260909")
    changes = main(do_apply)
    for qid, old, new, prompt in changes:
        print(f"  q{qid}: {chr(65+old)} -> {chr(65+new)}  {prompt[:40]}")
