#!/usr/bin/env python3
"""data/load_junyi.py

从 Junyi Academy 真实学习数据（Info_Content / Info_UserData / Log_Problem）
提取 PACE 实验所需的真实校准参数：

  - 18 个真实 KP（按 level3 聚合 elementary + math + Exercise）
  - 100 个真实 elementary 学生（theta 来自 Rasch 拟合）
  - 真实答题记录 sample（供 synthesize_d_real_from_junyi 使用）

保留 misconceptions / STYLES / MOTIVATION 定义（Junyi 无此信号）。

用法：
    python data/load_junyi.py --all --seed 42
        # 输出：data/knowledge_graph_junyi.json
        #       data/students_100_junyi.json
        #       data/junyi_irt_params.json   (全量 theta/b + ucid→level3 映射)
        #       data/junyi_real_interactions.jsonl (7500 条真实答题三元组)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp

sys.path.insert(0, str(Path(__file__).parent))
from _kp_definitions import (
    MISCONCEPTIONS, STYLES, STYLE_PRIORS,
    MOTIVATION_LEVELS, DIFFICULTY_OFFSETS,
)


# ============== 1. 数据加载与过滤 ==============

def load_and_filter(data_dir: Path):
    """加载三个 CSV，过滤为 elementary + math + Exercise + grade 1-6

    Returns:
        content_df, user_df, log_df (均已过滤)
    """
    print(f"[1/5] 加载 Junyi 原始 CSV（{data_dir}）...")
    content = pd.read_csv(data_dir / "Info_Content.csv")
    user = pd.read_csv(data_dir / "Info_UserData.csv")

    # 内容过滤
    content = content[
        (content["learning_stage"] == "elementary")
        & (content["subject"] == "math")
        & (content["content_kind"] == "Exercise")
    ].reset_index(drop=True)
    print(f"     elementary math exercises: {len(content)} 道")

    # 学生过滤（小学 1-6 年级）
    user = user[
        (user["user_grade"] >= 1) & (user["user_grade"] <= 6)
    ].reset_index(drop=True)
    print(f"     elementary students (G1-6): {len(user)}")

    # Log：只读必要列，按过滤后 uuid/ucid 筛
    valid_ucids = set(content["ucid"])
    valid_uuids = set(user["uuid"])

    print(f"     读取 Log_Problem.csv（16M 行，只保留过滤后的 uuid/ucid）...")
    log_iter = pd.read_csv(
        data_dir / "Log_Problem.csv",
        usecols=["uuid", "ucid", "is_correct", "total_sec_taken"],
        chunksize=2_000_000,
    )
    chunks = []
    for i, chunk in enumerate(log_iter):
        chunk = chunk[
            chunk["uuid"].isin(valid_uuids) & chunk["ucid"].isin(valid_ucids)
        ]
        chunks.append(chunk)
        print(f"       chunk {i+1} 保留 {len(chunk)} 条")
    log = pd.concat(chunks, ignore_index=True)
    log["is_correct"] = log["is_correct"].astype(int)
    print(f"     过滤后日志: {len(log):,} 条")
    return content, user, log


# ============== 2. KP 聚合 + 命名 ==============

# 关键词 → domain 规则（优先级从高到低，越具体越前）
DOMAIN_RULES = [
    (r"長條圖|折線圖|圓形圖|表格|統計",                     "statistics"),
    (r"毫升|公升|公斤|公克|毫米|公尺|公升與|體積：立方公分",  "measurement"),
    (r"時.{0,2}分.{0,2}秒|小時|分鐘",                        "time"),
    (r"小數|百分|比率|百分率",                              "decimal"),
    (r"分數",                                              "fraction"),
    (r"因數|倍數",                                          "factor"),
    (r"比[、，]?比值|比例|正比|反比",                        "ratio"),
    (r"體積|立方",                                          "geometry"),
    (r"面積|周長|平方公分",                                  "geometry"),
    (r"角度|三角形|圓形(?!圖)|正方形|長方形",                "geometry"),
    (r"雞兔|和差|年齡問題|數量關係|x\+a|兩步驟|三步驟|方程",  "wordprob"),
    (r"乘法|除法|加法|減法|加與|減與|乘與|除與",              "integer_op"),
    (r"整數|大數|讀寫|位值|十進位|過十|過百|過千",            "integer"),
]


def _strip_prefix(s: str) -> str:
    """去掉【基礎】【進階】等前缀"""
    s = re.sub(r"【[^】]+】\s*", "", s)
    s = re.sub(r"\s+\d+$", "", s)  # 去尾巴的 " 1" " 2"
    return s.strip()


def _infer_kp_name(pretty_names: list[str]) -> str:
    """从一组 pretty_name 里提取主题（取最频繁前缀）"""
    clean = [_strip_prefix(n) for n in pretty_names if n]
    if not clean:
        return "未命名"
    # 取前 12 字的众数
    prefixes = [n[:12] for n in clean]
    most = Counter(prefixes).most_common(1)[0][0]
    return most


def _infer_domain(pretty_names: list[str]) -> str:
    """每个 pretty_name 单独分类，取众数（避免不相关题名误触发）"""
    votes = []
    for n in pretty_names:
        for pattern, d in DOMAIN_RULES:
            if re.search(pattern, n):
                votes.append(d)
                break
    if not votes:
        return "misc"
    return Counter(votes).most_common(1)[0][0]


def _infer_grade(pretty_names: list[str], l2_domain: str) -> int:
    """根据主题粗估年级（Junyi learning_stage 已是 elementary）"""
    text = " ".join(pretty_names)
    if re.search(r"比例|百分率|正比|反比|複合形體|體積公式", text):
        return 6
    if re.search(r"體積|三角形面積|分數乘|小數乘|平均數", text):
        return 5
    if re.search(r"分數加|分數減|因數|倍數|角度|量角器|梯形", text):
        return 4
    if re.search(r"乘法和除法|面積|小數|時.{0,2}分.{0,2}秒|毫米|公斤|公克", text):
        return 3
    if re.search(r"二位數|進位|借位|九九|公分綜合", text):
        return 2
    if re.search(r"數到|一位數", text):
        return 1
    return 3


def build_kp_nodes(content: pd.DataFrame, b_by_ucid: dict[str, float]) -> tuple[list[dict], dict]:
    """按 level3 聚合，生成 KP 节点列表。

    Returns:
        nodes: [{id, name, domain, grade, b, difficulty_levels, applicable_misconceptions,
                 _junyi_level3_id, _junyi_ucids}]
        ucid_to_kp: {ucid: kp_id}
    """
    print(f"\n[3/5] 构建 KP nodes（按 level3 聚合）...")
    nodes = []
    ucid_to_kp = {}
    kp_to_mcs = defaultdict(list)
    for mc in MISCONCEPTIONS:
        for kp_id in mc["applies_to"]:
            kp_to_mcs[kp_id].append(mc["id"])

    # 按 level3 groupby
    for i, (l3_id, grp) in enumerate(
        content.groupby("level3_id", sort=False), start=1
    ):
        kp_id = f"k{i:02d}"
        pretty_names = grp["content_pretty_name"].tolist()
        name = _infer_kp_name(pretty_names)
        domain = _infer_domain(pretty_names)
        grade = _infer_grade(pretty_names, domain)

        # b 取该 level3 下所有 ucid 的 b 均值（需要 b_by_ucid 已估计）
        bs = [b_by_ucid[uc] for uc in grp["ucid"] if uc in b_by_ucid]
        b_kp = float(np.mean(bs)) if bs else 0.0

        node = {
            "id": kp_id,
            "name": name,
            "domain": domain,
            "grade": grade,
            "b": round(b_kp, 3),
            "difficulty_levels": [1, 2, 3, 4, 5],
            "applicable_misconceptions": [],  # 先空，稍后按 domain 启发式挂
            "_junyi_level3_id": l3_id,
            "_junyi_n_items": len(grp),
            "_junyi_l2_id": grp["level2_id"].iloc[0],
        }
        nodes.append(node)
        for uc in grp["ucid"]:
            ucid_to_kp[uc] = kp_id

    # 把合成的 misconceptions 启发式挂到 domain 匹配的 KP 上
    domain_to_mc = {
        "integer_op":  ["m01", "m02", "m03"],
        "integer":     ["m01", "m02"],
        "fraction":    ["m05", "m06", "m07", "m08"],
        "decimal":     ["m09", "m10"],
        "geometry":    ["m11", "m12", "m13"],
        "wordprob":    ["m14"],
        "ratio":       ["m15"],
        "measurement": ["m09"],
        "time":        [],
        "factor":      [],
        "statistics":  [],
        "misc":        [],
    }
    for n in nodes:
        n["applicable_misconceptions"] = domain_to_mc.get(n["domain"], [])

    print(f"     {len(nodes)} 个 KP:")
    for n in nodes:
        print(f"       {n['id']} [{n['domain']:12s}] G{n['grade']} b={n['b']:+.2f}  {n['name']}")
    return nodes, ucid_to_kp


# ============== 3. Rasch (1PL) IRT 拟合 ==============

def logit(p: np.ndarray, eps: float = 0.01) -> np.ndarray:
    p = np.clip(p, eps, 1.0 - eps)
    return np.log(p / (1.0 - p))


def fit_rasch(
    log: pd.DataFrame,
    n_iter: int = 5,
    min_items_per_user: int = 10,
    min_users_per_item: int = 20,
) -> tuple[dict, dict, pd.DataFrame]:
    """Rasch 交替估计 (theta, b)，稀疏矩阵加速。

    过滤：答题 >= min_items 的学生；被答 >= min_users 的题
    迭代：5 次（稳定收敛）
    身份约束：sum(theta)=0（消除平移自由度）

    Returns:
        theta_by_uuid: {uuid: float}
        b_by_ucid:    {ucid: float}
        filtered_log
    """
    print(f"\n[2/5] Rasch (1PL) IRT 拟合（稀疏交替法）...")

    # 过滤稀疏交互
    user_cnt = log.groupby("uuid").size()
    valid_u = set(user_cnt[user_cnt >= min_items_per_user].index)
    item_cnt = log.groupby("ucid").size()
    valid_i = set(item_cnt[item_cnt >= min_users_per_item].index)
    log = log[log["uuid"].isin(valid_u) & log["ucid"].isin(valid_i)].copy()
    print(f"     过滤: {len(valid_u):,} 学生 × {len(valid_i):,} 题 → {len(log):,} 交互")

    # 构索引
    users = sorted(valid_u)
    items = sorted(valid_i)
    u_idx = {u: i for i, u in enumerate(users)}
    i_idx = {it: j for j, it in enumerate(items)}
    n_u, n_i = len(users), len(items)

    rows = log["uuid"].map(u_idx).values.astype(np.int32)
    cols = log["ucid"].map(i_idx).values.astype(np.int32)
    y = log["is_correct"].values.astype(np.float32)
    resp = np.ones_like(y)

    # 稀疏 (n_u, n_i)
    Y = sp.csr_matrix((y, (rows, cols)), shape=(n_u, n_i))
    R = sp.csr_matrix((resp, (rows, cols)), shape=(n_u, n_i))

    u_sum_resp = np.asarray(R.sum(axis=1)).flatten()  # (n_u,)
    i_sum_resp = np.asarray(R.sum(axis=0)).flatten()  # (n_i,)
    u_sum_correct = np.asarray(Y.sum(axis=1)).flatten()
    i_sum_correct = np.asarray(Y.sum(axis=0)).flatten()

    u_pcorr = u_sum_correct / np.maximum(u_sum_resp, 1)
    i_pcorr = i_sum_correct / np.maximum(i_sum_resp, 1)

    theta = logit(u_pcorr).astype(np.float64)
    b = (-logit(i_pcorr)).astype(np.float64)

    # 交替迭代
    for it_num in range(1, n_iter + 1):
        # 更新 theta
        # mean_b_by_user = (R @ b) / u_sum_resp
        mean_b_u = (R @ b) / np.maximum(u_sum_resp, 1)
        theta_new = logit(u_pcorr) + mean_b_u

        # 中心化（消除平移）
        theta_new -= theta_new.mean()

        # 更新 b
        mean_theta_i = (R.T @ theta_new) / np.maximum(i_sum_resp, 1)
        b_new = -logit(i_pcorr) + mean_theta_i

        # 监控收敛
        d_theta = np.abs(theta_new - theta).mean()
        d_b = np.abs(b_new - b).mean()
        print(f"     iter {it_num}: Δtheta={d_theta:.4f}  Δb={d_b:.4f}")
        theta, b = theta_new, b_new

    theta_dict = {users[i]: float(theta[i]) for i in range(n_u)}
    b_dict = {items[j]: float(b[j]) for j in range(n_i)}
    print(f"     theta 统计: mean={theta.mean():+.3f} std={theta.std():.3f} "
          f"range=[{theta.min():.2f}, {theta.max():.2f}]")
    print(f"     b 统计:     mean={b.mean():+.3f} std={b.std():.3f} "
          f"range=[{b.min():.2f}, {b.max():.2f}]")
    return theta_dict, b_dict, log


# ============== 4. 学生采样 ==============

def sample_students(
    user: pd.DataFrame,
    theta_by_uuid: dict,
    log: pd.DataFrame,
    ucid_to_kp: dict,
    nodes: list[dict],
    n: int = 100,
    rng: np.random.Generator | None = None,
) -> list[dict]:
    """从有 theta 估计的学生里采 n 个，构造 PACE 学生档案。

    motivation 从 badges_cnt 启发式推断；style/misconceptions 按原分布合成；
    initial_mastery 用学生在各 KP 下的历史正确率（没答过的 KP 用 sigmoid(theta - b)）
    """
    print(f"\n[4/5] 采样 {n} 个真实学生...")
    rng = rng or np.random.default_rng(42)

    valid_uuids = [u for u in user["uuid"] if u in theta_by_uuid]
    print(f"     有 theta 估计的 G1-6 学生: {len(valid_uuids)}")
    picks = rng.choice(valid_uuids, size=n, replace=False)

    user_lookup = user.set_index("uuid")
    kp_ids = [n["id"] for n in nodes]
    kp_b = {n["id"]: n["b"] for n in nodes}

    # 预计算每个学生在每个 KP 下的答题正确率
    log_with_kp = log.copy()
    log_with_kp["kp_id"] = log_with_kp["ucid"].map(ucid_to_kp)
    log_with_kp = log_with_kp.dropna(subset=["kp_id"])
    student_kp_pcorr = (
        log_with_kp.groupby(["uuid", "kp_id"])["is_correct"]
        .mean()
        .unstack(fill_value=np.nan)
    )

    students = []
    for i, uuid in enumerate(picks, start=1):
        theta = theta_by_uuid[uuid]
        urow = user_lookup.loc[uuid]
        badges = int(urow.get("badges_cnt", 0))
        grade = int(urow.get("user_grade", 3))

        # motivation 启发式
        if badges >= 4:
            motivation = 2
        elif badges >= 1:
            motivation = 1
        else:
            motivation = 0

        style = str(rng.choice(STYLES, p=STYLE_PRIORS))

        # misconceptions：theta 低的多，高的少（与原合成规则一致）
        if theta >= 0.7:
            n_mcs = rng.choice([0, 1], p=[0.7, 0.3])
        elif theta >= 0.0:
            n_mcs = rng.choice([0, 1, 2], p=[0.3, 0.5, 0.2])
        elif theta >= -0.7:
            n_mcs = rng.choice([1, 2, 3], p=[0.3, 0.5, 0.2])
        else:
            n_mcs = rng.choice([2, 3, 4], p=[0.3, 0.5, 0.2])
        mc_ids = [mc["id"] for mc in MISCONCEPTIONS]
        mcs = (
            rng.choice(mc_ids, size=min(n_mcs, len(mc_ids)), replace=False).tolist()
            if n_mcs > 0 else []
        )

        # initial_mastery：用真实历史正确率，缺失用 sigmoid(theta - b)
        mastery = {}
        stud_row = student_kp_pcorr.loc[uuid] if uuid in student_kp_pcorr.index else None
        for kp in kp_ids:
            if stud_row is not None and kp in stud_row.index and not pd.isna(stud_row[kp]):
                m = float(stud_row[kp])
            else:
                m = float(1.0 / (1.0 + np.exp(-(theta - kp_b[kp]))))
            # 加点噪声 + clip
            m = float(np.clip(m + rng.normal(0, 0.05), 0.05, 0.98))
            mastery[kp] = round(m, 3)

        students.append({
            "id": f"s{i:03d}",
            "theta": round(float(theta), 3),
            "motivation": motivation,
            "style": style,
            "misconception_ids": mcs,
            "initial_mastery": mastery,
            "_junyi_uuid": uuid,
            "_junyi_grade": grade,
            "_junyi_badges": badges,
        })

    # 统计
    thetas = [s["theta"] for s in students]
    print(f"     theta: mean={np.mean(thetas):+.2f}  std={np.std(thetas):.2f}  "
          f"range=[{min(thetas):.2f}, {max(thetas):.2f}]")
    print(f"     grades: {Counter(s['_junyi_grade'] for s in students)}")
    return students


# ============== 5. 真实交互抽样（供 d_real 合成） ==============

def sample_real_interactions(
    log: pd.DataFrame,
    students: list[dict],
    ucid_to_kp: dict,
    kp_by_id: dict,
    difficulty_by_ucid: dict,
    n: int = 7500,
    rng: np.random.Generator | None = None,
) -> list[dict]:
    """从 100 个采样学生的真实答题记录里抽 n 条，作为 d_real 合成的种子。

    输出每条：(student_id, junyi_uuid, ucid, kp_id, kp_name, is_correct,
               junyi_difficulty, total_sec_taken, difficulty_level_1to5)
    """
    print(f"\n[5/5] 抽样真实 {n} 条交互作为 d_real 种子...")
    rng = rng or np.random.default_rng(42)

    uuid_to_sid = {s["_junyi_uuid"]: s["id"] for s in students}
    my_uuids = set(uuid_to_sid)
    my_log = log[log["uuid"].isin(my_uuids)].copy()
    print(f"     这 100 个学生的全部交互: {len(my_log):,}")

    # 过滤只有 kp_id 映射的交互
    my_log["kp_id"] = my_log["ucid"].map(ucid_to_kp)
    my_log = my_log.dropna(subset=["kp_id"])

    if len(my_log) > n:
        my_log = my_log.sample(n=n, random_state=int(rng.integers(1e9))).reset_index(drop=True)
    else:
        print(f"     实际只有 {len(my_log)} 条 < {n}，全部使用")

    diff_map = {"easy": 2, "normal": 3, "hard": 4, "unset": 3}
    records = []
    for _, row in my_log.iterrows():
        kp_id = row["kp_id"]
        kp = kp_by_id[kp_id]
        junyi_diff = difficulty_by_ucid.get(row["ucid"], "normal")
        level = diff_map.get(junyi_diff, 3)

        records.append({
            "student_id": uuid_to_sid[row["uuid"]],
            "junyi_uuid": row["uuid"],
            "ucid": row["ucid"],
            "kp_id": kp_id,
            "kp_name": kp["name"],
            "kp_domain": kp["domain"],
            "kp_grade": kp["grade"],
            "is_correct": bool(int(row["is_correct"])),
            "junyi_difficulty": junyi_diff,
            "difficulty_level": level,
            "total_sec_taken": int(row.get("total_sec_taken", 0)),
        })

    n_correct = sum(1 for r in records if r["is_correct"])
    print(f"     正确率: {n_correct}/{len(records)} = {n_correct/len(records)*100:.1f}%")
    return records


# ============== 主流程 ==============

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", default="data")
    parser.add_argument("--n_students", type=int, default=100)
    parser.add_argument("--n_interactions", type=int, default=7500)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n_iter", type=int, default=5)
    parser.add_argument("--min_items_per_user", type=int, default=10)
    parser.add_argument("--min_users_per_item", type=int, default=20)
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    rng = np.random.default_rng(args.seed)

    # Step 1: 加载 + 过滤
    content, user, log = load_and_filter(data_dir)

    # Step 2: Rasch 拟合
    theta_dict, b_dict, log_filtered = fit_rasch(
        log, n_iter=args.n_iter,
        min_items_per_user=args.min_items_per_user,
        min_users_per_item=args.min_users_per_item,
    )

    # Step 3: KP 节点
    nodes, ucid_to_kp = build_kp_nodes(content, b_dict)
    kp_by_id = {n["id"]: n for n in nodes}

    # Step 4: 学生采样
    students = sample_students(
        user, theta_dict, log_filtered, ucid_to_kp, nodes,
        n=args.n_students, rng=rng,
    )

    # Step 5: 真实交互抽样
    difficulty_by_ucid = dict(zip(content["ucid"], content["difficulty"]))
    interactions = sample_real_interactions(
        log_filtered, students, ucid_to_kp, kp_by_id,
        difficulty_by_ucid, n=args.n_interactions, rng=rng,
    )

    # ============== 组装输出 ==============

    # edges：level2 → level3 的层级边（作为 prerequisite）
    # 同 level2 内部 level3 按 b 从小到大串成链（粗略）
    edges = []
    by_l2 = defaultdict(list)
    for n in nodes:
        by_l2[n["_junyi_l2_id"]].append(n)
    for l2_id, group in by_l2.items():
        group_sorted = sorted(group, key=lambda x: x["b"])
        for u, v in zip(group_sorted[:-1], group_sorted[1:]):
            edges.append({"from": u["id"], "to": v["id"], "type": "prerequisite"})

    # domain 跨组边（简单规则：integer → fraction → decimal；integer → geometry/wordprob）
    domain_chain = [
        ("integer", "integer_op"),
        ("integer_op", "fraction"),
        ("fraction", "decimal"),
        ("integer_op", "geometry"),
        ("integer_op", "wordprob"),
        ("wordprob", "ratio"),
        ("measurement", "geometry"),
    ]
    for d_from, d_to in domain_chain:
        src = [n for n in nodes if n["domain"] == d_from]
        dst = [n for n in nodes if n["domain"] == d_to]
        if src and dst:
            src_hardest = max(src, key=lambda x: x["b"])
            dst_easiest = min(dst, key=lambda x: x["b"])
            edges.append({
                "from": src_hardest["id"], "to": dst_easiest["id"],
                "type": "prerequisite",
            })

    kg = {
        "metadata": {
            "source": "Junyi Academy (Kaggle: learning-activity-public-dataset-by-junyi-academy)",
            "domain": "primary_school_math",
            "language": "zh-TW",
            "n_kp": len(nodes),
            "n_edges": len(edges),
            "n_misconceptions": len(MISCONCEPTIONS),
            "schema_version": "2.0-junyi",
            "irt_params": "Rasch (1PL), alternating MLE, " + f"{args.n_iter} iter",
            "note": ("KP 按 level3_id 聚合；theta/b 从 72K 学生 × 1.6M 交互拟合；"
                     "misconceptions 沿用合成版本（Junyi 无此信号）"),
        },
        "nodes": nodes,
        "edges": edges,
        "misconceptions": MISCONCEPTIONS,
        "difficulty_offsets": {str(k): v for k, v in DIFFICULTY_OFFSETS.items()},
    }

    out_kg = data_dir / "knowledge_graph_junyi.json"
    out_kg.write_text(json.dumps(kg, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ 知识图谱 → {out_kg} ({out_kg.stat().st_size/1024:.1f} KB)")
    print(f"   {len(nodes)} KP, {len(edges)} edges")

    out_stu = data_dir / "students_100_junyi.json"
    out_stu.write_text(json.dumps(students, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ 学生档案 → {out_stu} ({out_stu.stat().st_size/1024:.1f} KB)")

    out_inter = data_dir / "junyi_real_interactions.jsonl"
    out_inter.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in interactions),
        encoding="utf-8",
    )
    print(f"✅ 真实交互 → {out_inter} ({out_inter.stat().st_size/1024:.1f} KB, "
          f"{len(interactions)} 条)")

    # 保存 IRT 参数（便于审稿人复现 + 其它脚本调用）
    irt_out = data_dir / "junyi_irt_params.json"
    irt_out.write_text(
        json.dumps({
            "method": "Rasch (1PL) alternating MLE",
            "n_iter": args.n_iter,
            "n_students_fit": len(theta_dict),
            "n_items_fit": len(b_dict),
            "theta_stats": {
                "mean": float(np.mean(list(theta_dict.values()))),
                "std": float(np.std(list(theta_dict.values()))),
            },
            "b_stats": {
                "mean": float(np.mean(list(b_dict.values()))),
                "std": float(np.std(list(b_dict.values()))),
            },
            "ucid_to_kp": ucid_to_kp,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"✅ IRT 元信息 → {irt_out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
