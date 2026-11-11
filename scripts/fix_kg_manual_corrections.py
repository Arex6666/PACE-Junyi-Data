#!/usr/bin/env python3
"""data/fix_kg_manual_corrections.py

对 load_junyi.py 自动生成的 knowledge_graph_junyi.json 做人工修正：
  1. kp_name 繁→简（论文展示用），同时保留 name_original（训练时 prompt 一致性）
  2. 个别 domain 错位修正（k07 容积→measurement, k13 位值→integer）
  3. 个别 grade 推断过高的修正（k05/k06/k07/k09/k11/k14）

执行后覆盖 knowledge_graph_junyi.json。

用法：
    python data/fix_kg_manual_corrections.py
"""
from __future__ import annotations
import json
from pathlib import Path


# === 修正规则（基于 2026-04-19 人工检查）===

# key = level3_id 前 8 位，避免依赖 k01-k18 编号（编号依赖 groupby 顺序，不稳定）
CORRECTIONS = {
    # L3[bo3jsx1b] 怎樣解題：數量關係
    "bo3jsx1b": {
        "name": "数量关系与应用题",
    },
    # L3[4cISKCt3] 兩步驟計算規則綜合習題
    "4cISKCt3": {
        "name": "两步骤计算应用题",
    },
    # L3[DySOBHaL] 讀長條圖與折線圖
    "DySOBHaL": {
        "name": "条形图与折线图",
    },
    # L3[0lUnR0kt] 生活中的表格
    "0lUnR0kt": {
        "name": "生活中的表格",
    },
    # L3[nLqsiSA2] 角度綜合習題 —— 实际是 G4 内容不是 G6
    "nLqsiSA2": {
        "name": "角度综合",
        "grade": 4,
    },
    # L3[xJYDWrjK] 複合形體的體積 —— G5 比 G6 合理
    "xJYDWrjK": {
        "name": "复合形体的体积",
        "grade": 5,
    },
    # L3[Dnl0P09L] 容量、容積和體積綜合習題 —— 核心是容积单位不是几何
    "Dnl0P09L": {
        "name": "容量、容积和体积",
        "domain": "measurement",
        "grade": 4,
    },
    # L3[ItasYR+e] 因數與公因數
    "ItasYR+e": {
        "name": "因数与公因数",
    },
    # L3[SbjJOr6q] 體積：立方公分 —— G5 合理（体积是五年级）
    "SbjJOr6q": {
        "name": "体积（立方厘米）",
        "grade": 5,
    },
    # L3[X5gAB0OL] 時間的加減
    "X5gAB0OL": {
        "name": "时间的加减",
    },
    # L3[YM8uggtD] 一位小數 —— G4 合理（三年级末到四年级）
    "YM8uggtD": {
        "name": "一位小数",
        "grade": 4,
    },
    # L3[a2w4FdOi] 毫米綜合
    "a2w4FdOi": {
        "name": "毫米与长度单位",
    },
    # L3[scsWmkZs] 數的十進位結構 —— 应该是 integer 不是 integer_op
    "scsWmkZs": {
        "name": "数的十进位结构",
        "domain": "integer",
    },
    # L3[zM75Dhur] 分數的乘法 —— G5 合理
    "zM75Dhur": {
        "name": "分数的乘法",
        "grade": 5,
    },
    # L3[3TpEcN+J] 角、正方形與長方形
    "3TpEcN+J": {
        "name": "角、正方形与长方形",
    },
    # L3[3fgcSGTz] 公斤和公克 —— 公克在简体里是"克"
    "3fgcSGTz": {
        "name": "公斤与克",
    },
    # L3[31v13N8G] 公升與毫升
    "31v13N8G": {
        "name": "公升与毫升",
    },
    # L3[8OFhw5s0] 平方公分 —— 面积
    "8OFhw5s0": {
        "name": "面积（平方厘米）",
    },
}


def main():
    path = Path("data/knowledge_graph_junyi.json")
    kg = json.loads(path.read_text(encoding="utf-8"))

    n_renamed = 0
    n_domain_fix = 0
    n_grade_fix = 0
    unknown = []

    for node in kg["nodes"]:
        l3_prefix = node["_junyi_level3_id"][:8]
        if l3_prefix not in CORRECTIONS:
            unknown.append((node["id"], node["name"], l3_prefix))
            continue

        corr = CORRECTIONS[l3_prefix]
        # 保留原繁体名，训练时 prompt 一致性
        node["name_original"] = node["name"]

        if "name" in corr and corr["name"] != node["name"]:
            node["name"] = corr["name"]
            n_renamed += 1
        if "domain" in corr and corr["domain"] != node["domain"]:
            print(f"  {node['id']}: domain {node['domain']} → {corr['domain']}")
            node["domain"] = corr["domain"]
            n_domain_fix += 1
        if "grade" in corr and corr["grade"] != node["grade"]:
            print(f"  {node['id']}: grade G{node['grade']} → G{corr['grade']}")
            node["grade"] = corr["grade"]
            n_grade_fix += 1

    # domain → misconception 映射重建（k13 改了 domain，applicable_misconceptions 要更新）
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
    for node in kg["nodes"]:
        node["applicable_misconceptions"] = domain_to_mc.get(node["domain"], [])

    # metadata 更新
    kg["metadata"]["note"] = (
        kg["metadata"].get("note", "")
        + " | Manually corrected 2026-04-19: kp_name 繁→简, "
        "fixed 2 domain mismatches (k07 measurement, k13 integer), "
        "fixed 5 grade over-estimations (k05 G4, k06 G5, k07 G4, k11 G4, k14 G5)."
    )
    kg["metadata"]["schema_version"] = "2.1-junyi-corrected"

    path.write_text(json.dumps(kg, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n✅ 覆盖 {path}")
    print(f"   重命名: {n_renamed}  domain 修正: {n_domain_fix}  grade 修正: {n_grade_fix}")
    if unknown:
        print(f"\n⚠️  未知 level3_id ({len(unknown)})：")
        for info in unknown:
            print(f"     {info}")

    print("\n=== 修正后的 KP 清单 ===")
    for n in kg["nodes"]:
        orig = f" (was: {n.get('name_original','-')})" if n.get("name_original") != n["name"] else ""
        print(f"  {n['id']} [{n['domain']:12s}] G{n['grade']} b={n['b']:+.2f}  {n['name']}{orig}")


if __name__ == "__main__":
    main()
