"""data/_kp_definitions.py

PACE 实验数据的"单一真理来源"——25 个小学数学知识点 + 15 类典型误解。

下游脚本（build_knowledge_graph / generate_students / synthesize_real_answers /
generate_seed_trajectories）都从这里导入，避免分散维护。

**Step B 替换计划**：未来用 Junyi Knowledge Map 真实 KP 替换本文件，
其他脚本无需改动（接口保持 KP_LIST / EDGES / MISCONCEPTIONS 不变）。
"""

# === 知识点定义 ===
# 每个 KP：id, name (中文), domain, grade (小学几年级), b (IRT 难度参数)
#
# b 的语义：在 IRT 中，P(正确) = sigmoid(theta - b - d_diff_level)
# b 越大，KP 整体越难（弱学生 theta 接近 0 时，b=1.5 比 b=0 难得多）
# 我们按"概念递进"由浅到深排 b：基础整数运算 b≈0，分数/小数 b≈0.5-1，几何/应用 b≈1-1.5

KP_LIST = [
    # 整数运算 (6)
    {"id": "k01", "name": "一位数加法",       "domain": "integer",   "grade": 1, "b": -0.5},
    {"id": "k02", "name": "一位数减法",       "domain": "integer",   "grade": 1, "b": -0.3},
    {"id": "k03", "name": "两位数加法（进位）", "domain": "integer",   "grade": 2, "b":  0.0},
    {"id": "k04", "name": "两位数减法（借位）", "domain": "integer",   "grade": 2, "b":  0.2},
    {"id": "k05", "name": "乘法（九九表）",     "domain": "integer",   "grade": 2, "b":  0.1},
    {"id": "k06", "name": "除法（一位数除）",   "domain": "integer",   "grade": 3, "b":  0.4},
    # 分数 (5)
    {"id": "k07", "name": "分数概念",          "domain": "fraction",  "grade": 3, "b":  0.5},
    {"id": "k08", "name": "同分母分数加法",     "domain": "fraction",  "grade": 3, "b":  0.6},
    {"id": "k09", "name": "异分母分数加法",     "domain": "fraction",  "grade": 4, "b":  1.0},
    {"id": "k10", "name": "分数减法",          "domain": "fraction",  "grade": 4, "b":  0.9},
    {"id": "k11", "name": "分数乘法",          "domain": "fraction",  "grade": 4, "b":  1.0},
    # 小数 (4)
    {"id": "k12", "name": "小数概念",          "domain": "decimal",   "grade": 3, "b":  0.5},
    {"id": "k13", "name": "小数加法",          "domain": "decimal",   "grade": 4, "b":  0.7},
    {"id": "k14", "name": "小数减法",          "domain": "decimal",   "grade": 4, "b":  0.7},
    {"id": "k15", "name": "小数乘法",          "domain": "decimal",   "grade": 5, "b":  1.1},
    # 几何 (4)
    {"id": "k16", "name": "周长（矩形）",       "domain": "geometry",  "grade": 3, "b":  0.6},
    {"id": "k17", "name": "面积（矩形）",       "domain": "geometry",  "grade": 3, "b":  0.7},
    {"id": "k18", "name": "面积（三角形）",     "domain": "geometry",  "grade": 5, "b":  1.2},
    {"id": "k19", "name": "体积（长方体）",     "domain": "geometry",  "grade": 5, "b":  1.3},
    # 应用题 (4)
    {"id": "k20", "name": "加减法应用题",       "domain": "wordprob",  "grade": 2, "b":  0.5},
    {"id": "k21", "name": "乘除法应用题",       "domain": "wordprob",  "grade": 3, "b":  0.8},
    {"id": "k22", "name": "倍数关系",          "domain": "wordprob",  "grade": 4, "b":  1.0},
    {"id": "k23", "name": "比与比例",          "domain": "wordprob",  "grade": 6, "b":  1.5},
    # 统计 (2)
    {"id": "k24", "name": "平均数",            "domain": "statistics", "grade": 4, "b":  0.8},
    {"id": "k25", "name": "百分比",            "domain": "statistics", "grade": 6, "b":  1.4},
]

# === 前序依赖（DAG 边） ===
# (from, to) 表示"学了 from 才能学 to"
EDGES = [
    # 整数链
    ("k01", "k02"), ("k01", "k03"), ("k02", "k04"),
    ("k03", "k05"), ("k05", "k06"), ("k03", "k20"), ("k04", "k20"),
    # 分数链
    ("k07", "k08"), ("k08", "k09"), ("k08", "k10"), ("k09", "k10"),
    ("k09", "k11"), ("k05", "k11"),
    # 小数链
    ("k12", "k13"), ("k12", "k14"), ("k13", "k14"),
    ("k13", "k15"), ("k14", "k15"), ("k05", "k15"),
    # 几何链
    ("k16", "k17"), ("k17", "k18"), ("k17", "k19"),
    # 应用题链
    ("k20", "k21"), ("k06", "k21"), ("k21", "k22"), ("k22", "k23"),
    # 统计需要混合基础
    ("k20", "k24"), ("k24", "k25"), ("k09", "k25"), ("k15", "k25"),
]

# === 难度档位修正 d_diff(level) ===
# 5 个档位：L1 最简单 (d=-1.0)，L5 最难 (d=+1.0)
# 用于 IRT: P(正确) = sigmoid(theta - b_kp - d_diff_level)
DIFFICULTY_OFFSETS = {1: -1.0, 2: -0.5, 3: 0.0, 4: +0.5, 5: +1.0}


# === 误解定义 ===
# 每个误解：id, name (中文), description (机制), applies_to (适用 KP 列表),
# wrong_answer_template (错误答案模板，用于合成 D_real 时生成"似是而非"的错答)
MISCONCEPTIONS = [
    {
        "id": "m01", "name": "加法忘进位",
        "description": "做加法时不记进位，个位结果错误",
        "applies_to": ["k03", "k20"],
        "wrong_pattern": "drop_carry",  # 算 17+5 时给 12（直接 7+5 进位扔了）
    },
    {
        "id": "m02", "name": "减法忘借位",
        "description": "做减法时不会借位，遇到不够减用绝对值",
        "applies_to": ["k04", "k20"],
        "wrong_pattern": "abs_borrow",  # 算 23-7 时给 24（|3-7|=4）
    },
    {
        "id": "m03", "name": "乘法表混淆",
        "description": "九九表中相邻题的混淆，如 7×8=54 / 56 / 64",
        "applies_to": ["k05", "k21"],
        "wrong_pattern": "table_neighbor",
    },
    {
        "id": "m04", "name": "除法商错位",
        "description": "竖式除法时商的位置错（少一位或多一位）",
        "applies_to": ["k06"],
        "wrong_pattern": "quotient_misalign",
    },
    {
        "id": "m05", "name": "分数加法分母相加",
        "description": "异分母分数加法把分母直接相加：1/2+1/3=2/5",
        "applies_to": ["k09"],
        "wrong_pattern": "frac_add_denom",  # ★ 经典误解
    },
    {
        "id": "m06", "name": "分数加法分子分母都加",
        "description": "把分子和分母分别相加：1/2+1/3=2/5",
        "applies_to": ["k08", "k09"],
        "wrong_pattern": "frac_add_both",
    },
    {
        "id": "m07", "name": "分数减法忘通分",
        "description": "异分母减法忘了通分，分子直接相减",
        "applies_to": ["k10"],
        "wrong_pattern": "frac_sub_no_lcm",
    },
    {
        "id": "m08", "name": "分数乘法只乘分子",
        "description": "做分数乘法只乘分子，分母保留：2/3 × 4/5 = 8/3",
        "applies_to": ["k11"],
        "wrong_pattern": "frac_mul_num_only",
    },
    {
        "id": "m09", "name": "小数点对齐错误",
        "description": "小数加减时按右端对齐而非小数点对齐",
        "applies_to": ["k13", "k14"],
        "wrong_pattern": "dec_align_right",
    },
    {
        "id": "m10", "name": "小数乘法忘小数点",
        "description": "小数乘法做完忘了点小数点，结果放大 10/100 倍",
        "applies_to": ["k15"],
        "wrong_pattern": "dec_mul_no_point",
    },
    {
        "id": "m11", "name": "周长面积混淆",
        "description": "把周长公式当面积用，或反过来",
        "applies_to": ["k16", "k17"],
        "wrong_pattern": "perim_area_swap",
    },
    {
        "id": "m12", "name": "三角形面积忘除以 2",
        "description": "把三角形面积直接算成 底 × 高",
        "applies_to": ["k18"],
        "wrong_pattern": "tri_area_no_half",
    },
    {
        "id": "m13", "name": "长方体表面积当体积",
        "description": "求体积时算成 6 个面之和",
        "applies_to": ["k19"],
        "wrong_pattern": "vol_use_surf",
    },
    {
        "id": "m14", "name": "应用题反向运算",
        "description": "应用题该加用减、该乘用除，对'共'/'剩'/'倍'语义混淆",
        "applies_to": ["k20", "k21", "k22"],
        "wrong_pattern": "wp_reverse",
    },
    {
        "id": "m15", "name": "比例颠倒",
        "description": "比例题中前后项颠倒，如 3:5 当 5:3 用",
        "applies_to": ["k23"],
        "wrong_pattern": "ratio_inverse",
    },
]

# === 学生属性的分布参数 ===
STYLES = ["concrete", "abstract", "memorization", "inquiry"]
STYLE_PRIORS = [0.35, 0.20, 0.25, 0.20]  # 小学生具体风格偏多

MOTIVATION_LEVELS = [0, 1, 2]  # 低 / 中 / 高
MOTIVATION_PRIORS = [0.20, 0.55, 0.25]
