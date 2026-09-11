"""Level 5 答案位置重排（2026-09-11）

背景：L5 共 90 题，88 题 correct_index=0（答案全在 A），学员可纯靠位置秒杀。
      根因是 seed_level5.py 写库时正确项永远放位置 0，未套用 L4 之后确立的
      "写库时就把正确项放目标位置" 约定。

规则（沿用 rebalance_l4_answers_20260909.py 的口径）：
- 已作答的题（quiz_answer_log 有记录）冻结，保持原位置不动，重排会让历史记录语义错位。
- L5 中无顺序敏感题（options 是天然 0/1/2/3 序列），无需 FROZEN_QID。
- 每课 10 题套用规范的目标序列 [2,0,3,1,0,3,1,2,3,1]（A/B/C/D 计数 2/3/2/3），
  并按课序 rotate 以错开跨课位置规律，与 L6 既有设计保持一致。
- 重排方式：把正确项搬到目标位置，其余三个干扰项按原相对顺序填入空位
  （确定性、最小"看起来乱"的扰动，且不引入新文本）。
- 解析里没有写死选项字母（扫描 0 处），无需改写 explanation。

Level 6 已用同套序列、分布为 [22,23,22,23]，本次不处理。

用法：python rebalance_l5_answers_20260911.py [--apply]   # 默认 dry-run
"""

import json
import shutil
import sqlite3
import sys

DB = "spark_quest.db"
LEVEL_ORDER_INDEX = 5  # L5

# 规范的目标序列：第 q 题正确项应落在的位置（A/B/C/D 计数 = 2/3/2/3）
BASE_PER_Q = [2, 0, 3, 1, 0, 3, 1, 2, 3, 1]


def rotate(lst, k):
    k %= len(lst)
    return lst[k:] + lst[:k]


def rebalance_options(old_opts, old_ci, new_ci):
    """正确项搬到 new_ci，其余干扰项按原相对顺序填入剩余空位。"""
    correct = old_opts[old_ci]
    others = [old_opts[i] for i in range(len(old_opts)) if i != old_ci]
    new = [None] * len(old_opts)
    new[new_ci] = correct
    rest = [i for i in range(len(old_opts)) if i != new_ci]
    for j, slot in enumerate(rest):
        new[slot] = others[j]
    return new


def main(apply):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    # 已作答的题，冻结
    cur.execute("select distinct question_id from quiz_answer_log")
    logged = {r[0] for r in cur.fetchall()}

    cur.execute(
        """select q.id, q.lesson_id, q.options, q.correct_index, q.prompt
           from quizzes q join lessons l on l.id = q.lesson_id
           where l.level_id = (select id from course_levels where order_index = ?)
           order by q.lesson_id, q.order_index""",
        (LEVEL_ORDER_INDEX,),
    )
    rows = cur.fetchall()

    by_lesson = {}
    for qid, lid, opt_json, ci, prompt in rows:
        by_lesson.setdefault(lid, []).append(
            {"qid": qid, "opts": json.loads(opt_json), "ci": ci, "prompt": prompt}
        )

    lesson_ids = sorted(by_lesson)
    changes = []  # (qid, old_ci, new_ci, prompt)
    frozen_total = 0
    for g, lid in enumerate(lesson_ids):
        items = by_lesson[lid]
        target = rotate(BASE_PER_Q, g)
        for p, it in enumerate(items):
            if it["qid"] in logged:
                frozen_total += 1
                continue  # 冻结，保持原位置
            old_ci = it["ci"]
            new_ci = target[p]
            if old_ci == new_ci:
                continue
            new_opts = rebalance_options(it["opts"], old_ci, new_ci)
            # 校验：正确项文本必须一致
            assert new_opts[new_ci] == it["opts"][old_ci], f"q{it['qid']} 正确项文本不一致"
            it["opts"] = new_opts
            it["ci"] = new_ci
            changes.append((it["qid"], old_ci, new_ci, it["prompt"]))
            if apply:
                cur.execute(
                    "update quizzes set options=?, correct_index=? where id=?",
                    (json.dumps(new_opts, ensure_ascii=False), new_ci, it["qid"]),
                )

        # 打印本课结果分布
        seq = [it["ci"] for it in items]
        cnt = [seq.count(i) for i in range(4)]
        print(f"lesson {lid} (g={g}): target={target} -> {seq}  counts A/B/C/D={cnt}")

    if apply:
        conn.commit()
    conn.close()

    print()
    print(f"重排题数: {len(changes)}（共 {len(rows)} 题，冻结 {frozen_total} 题）")
    if not apply:
        print("dry-run，未写入。加 --apply 执行。")
    return changes


if __name__ == "__main__":
    do_apply = "--apply" in sys.argv
    if do_apply:
        shutil.copy(DB, DB + ".bak_before_l5rebalance_20260911")
        print("已备份:", DB + ".bak_before_l5rebalance_20260911")
    changes = main(do_apply)
    for qid, old, new, prompt in changes:
        print(f"  q{qid}: {chr(65+old)} -> {chr(65+new)}  {prompt[:36]}")
