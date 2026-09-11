"""把修正后的 L5 答案位置写回 seed_level5.py（2026-09-11）

背景：rebalance_l5_answers_20260911.py 已修正 spark_quest.db 中 L5 的 correct_index
分布（从 [88,2,0,0] 改为均衡分布）。但 seed_level5.py 的 LEVEL5_QUIZZES 仍把正确项
放位置 0，且因 2026-09-10 的 L5/L6 审计修复，DB 里有 2 题 prompt 已被改写而 seed 未同步
（这是另一处已知 drift，本次不改 prompt，只同步答案位置）。

做法（最小风险）：
- 用括号配平方式精确取出 LEVEL5_QUIZZES 块（ast.literal_eval 校验为纯字面量）。
- 按位置映射 seed[j] <-> DB[j]（两者都是 lessons 顺序、每课 10 题），只改每题的
  options 与 correct_index，其余字段（prompt/explanation/dimension...）原样保留。
- 整块用 json.dumps 重新序列化（合法 Python 字面量），原位替换。
- 写前备份；写后校验语法、可 literal_eval、分布与 DB 一致。

注意：seed 的 upsert 对已存在 quiz 的 lesson 会跳过，所以本改动只在「清空 L5 quiz 后重跑
seed」时生效；运行中的 DB 以 rebalance 脚本为准。
"""

import sqlite3, json, ast, shutil, re, sys

DB = "spark_quest.db"
SEED = "seed_level5.py"
L5 = [40, 41, 42, 43, 44, 45, 46, 47, 48]


def extract_block(src, name):
    idx = src.index(name + " = [")
    start = idx + len(name + " = ")
    depth = 0
    i = start
    while i < len(src):
        if src[i] == '[':
            depth += 1
        elif src[i] == ']':
            depth -= 1
            if depth == 0:
                break
        i += 1
    return start, i + 1, src[start:i + 1]


def main():
    # 1) 从 DB 取修正后的 L5 选项与正确下标（按 lesson/order_index 顺序）
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute(
        "select options, correct_index from quizzes where lesson_id in (%s) order by lesson_id, order_index"
        % ",".join(map(str, L5))
    )
    db = [(json.loads(r[0]), r[1]) for r in cur.fetchall()]
    con.close()
    assert len(db) == 90, f"DB L5 题数异常: {len(db)}"

    # 2) 取出 seed 块
    src = open(SEED, encoding="utf-8").read()
    start, end, block = extract_block(src, "LEVEL5_QUIZZES")
    data = ast.literal_eval(block)
    seed_q = [q for e in data for q in e["questions"]]
    assert len(seed_q) == 90, f"seed L5 题数异常: {len(seed_q)}"

    # 3) 位置映射，只改 options / correct_index
    changed = 0
    for j, q in enumerate(seed_q):
        new_opts, new_ci = db[j]
        if q["options"] != new_opts or q["correct_index"] != new_ci:
            q["options"] = new_opts
            q["correct_index"] = new_ci
            changed += 1

    # 4) 重新序列化并替换
    new_block = "[\n" + ",\n".join(
        json.dumps(e, ensure_ascii=False, indent=2) for e in data
    ) + "\n]"
    new_src = src[:start] + new_block + src[end:]

    bak = SEED + ".bak_before_l5seedfix_20260911"
    shutil.copy(SEED, bak)
    with open(SEED, "w", encoding="utf-8") as f:
        f.write(new_src)
    print("已备份:", bak)
    print(f"改写题目数: {changed} / 90")

    # 5) 校验
    ast.parse(new_src)  # 语法
    s2, e2, b2 = extract_block(new_src, "LEVEL5_QUIZZES")
    d2 = ast.literal_eval(b2)
    sq2 = [q for e in d2 for q in e["questions"]]
    from collections import Counter
    dist = Counter(q["correct_index"] for q in sq2)
    print("seed 改后 correct_index 分布 A/B/C/D:", [dist.get(i, 0) for i in range(4)])
    # 与 DB 逐题比对
    ok = all(sq2[j]["options"] == db[j][0] and sq2[j]["correct_index"] == db[j][1] for j in range(90))
    print("seed 与 DB 答案位置逐题一致:", ok)
    return ok


if __name__ == "__main__":
    ok = main()
    print("OK" if ok else "FAILED")
    sys.exit(0 if ok else 1)
