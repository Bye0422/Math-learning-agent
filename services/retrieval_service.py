import re
from copy import deepcopy

from langchain_core.documents import Document

import config

HYBRID_VECTOR_TOP_N = getattr(config, "HYBRID_VECTOR_TOP_N", 8)
HYBRID_RULE_TOP_N = getattr(config, "HYBRID_RULE_TOP_N", 8)

HYBRID_VECTOR_WEIGHT_WITH_REF = getattr(config, "HYBRID_VECTOR_WEIGHT_WITH_REF", 0.35)
HYBRID_RULE_WEIGHT_WITH_REF = getattr(config, "HYBRID_RULE_WEIGHT_WITH_REF", 0.65)

HYBRID_VECTOR_WEIGHT_NORMAL = getattr(config, "HYBRID_VECTOR_WEIGHT_NORMAL", 0.75)
HYBRID_RULE_WEIGHT_NORMAL = getattr(config, "HYBRID_RULE_WEIGHT_NORMAL", 0.25)


# =========================
# 中文数字转换
# =========================

CHINESE_NUM_MAP = {
    "零": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
}


def chinese_num_to_int(text):
    """
    支持：
    一、二、三、十、十一、十二、二十、二十一
    """
    if not text:
        return None

    text = text.strip()

    if text.isdigit():
        return int(text)

    if text in CHINESE_NUM_MAP:
        return CHINESE_NUM_MAP[text]

    if "十" in text:
        parts = text.split("十")

        # 十一、十二
        if parts[0] == "":
            ten_part = 1
        else:
            ten_part = CHINESE_NUM_MAP.get(parts[0], 0)

        if len(parts) > 1 and parts[1]:
            one_part = CHINESE_NUM_MAP.get(parts[1], 0)
        else:
            one_part = 0

        return ten_part * 10 + one_part

    return None


def normalize_section_ref(text):
    if not text:
        return None

    return text.strip().replace("．", ".")


def extract_section_reference(query):
    """
    提取章节/习题组编号，例如：
    - 3.1的第二题
    - 课后习题1.1中，第二题
    - 第3.1节第2题
    """
    if not query:
        return None

    section_patterns = [
        r"(?:课后习题|习题|练习|章节|第)\s*([0-9]{1,3}(?:[\.．][0-9]{1,3}){1,3})\s*(?:节|章|中|的)?",
        r"(?<![0-9])([0-9]{1,3}(?:[\.．][0-9]{1,3}){1,3})(?![0-9])",
    ]

    for pattern in section_patterns:
        match = re.search(pattern, query)

        if match:
            return normalize_section_ref(match.group(1))

    return None


# =========================
# 从用户问题中提取题型和题号
# =========================

def extract_question_reference(query):
    """
    从用户问题里提取：
    - question_type：选择题 / 判断题 / 填空题 / 计算题 / 简答题
    - question_number：题号数字

    例如：
    “选择题第二题怎么做” → 选择题, 2
    “第3题为什么选B” → None, 3
    “判断题第4题对不对” → 判断题, 4
    """
    question_type = None

    question_types = ["选择题", "判断题", "填空题", "计算题", "简答题"]

    for qt in question_types:
        if qt in query:
            question_type = qt
            break

    question_number = None
    option_letter = None
    section_ref = extract_section_reference(query)

    option_match = re.search(
        r"(?:选|选择|答案是|为什么选)\s*([A-D])",
        query,
        re.I,
    )

    if option_match:
        option_letter = option_match.group(1).upper()

    patterns = [
        r"第\s*[\(（]?([0-9]+)[\)）]?\s*(?:题|小题|问)",
        r"第\s*[\(（]?([一二两三四五六七八九十]+)[\)）]?\s*(?:题|小题|问)",
        r"(选择题|判断题|填空题|计算题|简答题)\s*第?\s*([0-9]+)\s*题?",
        r"(选择题|判断题|填空题|计算题|简答题)\s*第?\s*([一二两三四五六七八九十]+)\s*题?",
        r"(选择题|判断题|填空题|计算题|简答题)\s*([0-9]+)\s*题?",
        r"(选择题|判断题|填空题|计算题|简答题)\s*([一二两三四五六七八九十]+)\s*题?",
        r"[\(（]([0-9]+)[\)）]",
        r"[\(（]([一二两三四五六七八九十]+)[\)）]",
        r"([①②③④⑤⑥⑦⑧⑨⑩])",
        r"(?<![0-9\.．])([0-9]+)\s*[\.．、)](?![0-9])",
        r"([一二两三四五六七八九十]+)\s*[、\.．]",
    ]

    for pattern in patterns:
        match = re.search(pattern, query)

        if not match:
            continue

        groups = match.groups()

        if len(groups) == 1:
            num_text = groups[0]
        else:
            if groups[0] in question_types:
                question_type = groups[0]
                num_text = groups[1]
            else:
                num_text = groups[-1]

        circled_num_map = {
            "①": 1,
            "②": 2,
            "③": 3,
            "④": 4,
            "⑤": 5,
            "⑥": 6,
            "⑦": 7,
            "⑧": 8,
            "⑨": 9,
            "⑩": 10,
        }

        if num_text in circled_num_map:
            question_number = circled_num_map[num_text]
        elif num_text.isdigit():
            question_number = int(num_text)
        else:
            question_number = chinese_num_to_int(num_text)

        if question_number is not None:
            break

    return {
        "question_type": question_type,
        "question_number": question_number,
        "option_letter": option_letter,
        "section_ref": section_ref,
    }


# =========================
# 构造题号匹配模式
# =========================

def int_to_simple_chinese(num):
    """
    只做 1-99 的简单中文数字，用于生成匹配模式。
    """
    digit_to_cn = {
        0: "",
        1: "一",
        2: "二",
        3: "三",
        4: "四",
        5: "五",
        6: "六",
        7: "七",
        8: "八",
        9: "九",
    }

    if num <= 10:
        reverse_map = {
            1: "一",
            2: "二",
            3: "三",
            4: "四",
            5: "五",
            6: "六",
            7: "七",
            8: "八",
            9: "九",
            10: "十",
        }
        return reverse_map.get(num, str(num))

    if num < 20:
        return "十" + digit_to_cn[num % 10]

    ten = num // 10
    one = num % 10

    if one == 0:
        return digit_to_cn[ten] + "十"

    return digit_to_cn[ten] + "十" + digit_to_cn[one]


def build_question_number_patterns(question_number):
    """
    为题号生成多种可能出现方式。
    """
    if question_number is None:
        return []

    cn_num = int_to_simple_chinese(question_number)

    return [
        f"第{question_number}题",
        f"第 {question_number} 题",
        f"第{question_number}小题",
        f"第 {question_number} 小题",
        f"第{question_number}问",
        f"第 {question_number} 问",
        f"{question_number}.",
        f"{question_number}．",
        f"{question_number}、",
        f"{question_number})",
        f"({question_number})",
        f"（{question_number}）",
        f"题{question_number}",
        f"第{cn_num}题",
        f"第{cn_num}小题",
        f"第{cn_num}问",
        f"({cn_num})",
        f"（{cn_num}）",
        f"{cn_num}、",
        f"{cn_num}.",
        f"{cn_num}．",
    ]


def build_section_patterns(section_ref):
    """
    为章节/习题组编号生成常见写法。
    """
    section_ref = normalize_section_ref(section_ref)

    if not section_ref:
        return []

    fullwidth_section_ref = section_ref.replace(".", "．")

    return [
        section_ref,
        fullwidth_section_ref,
        f"第{section_ref}节",
        f"第 {section_ref} 节",
        f"第{fullwidth_section_ref}节",
        f"第 {fullwidth_section_ref} 节",
        f"习题{section_ref}",
        f"习题 {section_ref}",
        f"习题{fullwidth_section_ref}",
        f"课后习题{section_ref}",
        f"课后习题 {section_ref}",
        f"课后习题{fullwidth_section_ref}",
        f"练习{section_ref}",
        f"练习 {section_ref}",
        f"章节{section_ref}",
        f"章节 {section_ref}",
    ]


# =========================
# 关键词提取
# =========================

STOPWORDS = {
    "这个",
    "那个",
    "应该",
    "怎么",
    "为什么",
    "一下",
    "请问",
    "进行",
    "回答",
    "解释",
    "解析",
    "如何",
    "什么",
    "哪种",
    "哪个",
    "题",
    "第",
}


def extract_keywords(query):
    """
    简单关键词提取。
    不依赖 jieba，先用规则做基础版。
    """
    query = re.sub(r"[，。！？、,.!?：:；;（）()\[\]【】\"']", " ", query)

    tokens = re.findall(r"[\u4e00-\u9fa5]{2,}|[A-Za-z0-9_]+", query)

    keywords = []

    for token in tokens:
        token = token.strip()

        if not token:
            continue

        if token in STOPWORDS:
            continue

        if len(token) < 2:
            continue

        keywords.append(token)

    return list(dict.fromkeys(keywords))


# =========================
# 规则检索打分
# =========================

def calculate_rule_score(doc, query, question_ref):
    """
    给每个 chunk 一个规则分数。
    分数越高，说明越可能是题号/关键词命中的片段。
    """
    content = doc.page_content or ""
    metadata = doc.metadata or {}

    question_type = question_ref.get("question_type")
    question_number = question_ref.get("question_number")
    option_letter = question_ref.get("option_letter")
    section_ref = question_ref.get("section_ref")

    score = 0.0
    reasons = []
    matched_keywords = []
    metadata_text = " ".join(str(value) for value in metadata.values() if value)
    searchable_text = f"{content}\n{metadata_text}"

    # 题型命中
    if question_type and question_type in content:
        score += 5.0
        reasons.append(f"题型命中：{question_type}")

    # 章节/习题组命中。章节号常出现在页眉、标题或 chunk metadata 中，所以这里同时看 metadata。
    section_patterns = build_section_patterns(section_ref)
    section_hit = False

    for pattern in section_patterns:
        if pattern and pattern in searchable_text:
            section_hit = True
            score += 10.0
            reasons.append(f"章节命中：{pattern}")
            break

    # 题号命中
    number_patterns = build_question_number_patterns(question_number)
    number_hit = False

    for pattern in number_patterns:
        if pattern in content:
            number_hit = True
            score += 12.0
            reasons.append(f"题号命中：{pattern}")
            break

    if section_ref and question_number is not None and section_hit and number_hit:
        score += 18.0
        reasons.append("章节和题号同时命中")

    # 题型 + 题号同时命中，加权
    if question_type and question_number is not None:
        if question_type in content and any(p in content for p in number_patterns):
            score += 8.0
            reasons.append("题型和题号同时命中")

    if option_letter:
        option_patterns = [
            f"选{option_letter}",
            f"选 {option_letter}",
            f"答案{option_letter}",
            f"答案是{option_letter}",
            f"{option_letter}.",
            f"{option_letter}．",
            f"{option_letter}、",
        ]

        for pattern in option_patterns:
            if pattern in content:
                score += 3.0
                reasons.append(f"选项命中：{option_letter}")
                break

    # 用户关键词命中
    keywords = extract_keywords(query)

    for keyword in keywords:
        if keyword in content:
            matched_keywords.append(keyword)

    if keywords:
        keyword_score = len(matched_keywords) / len(keywords)
        score += keyword_score * 5.0

        if matched_keywords:
            reasons.append(f"关键词命中：{len(matched_keywords)}/{len(keywords)}")

    # location 只能作为已有命中后的轻微排序信号，不能单独让 chunk 进入规则候选。
    if score > 0 and metadata.get("location"):
        score += 0.1

    return score, reasons, matched_keywords


def rule_retrieve(chunks, query, top_n=HYBRID_RULE_TOP_N):
    """
    基于题号和关键词的规则检索。
    """
    question_ref = extract_question_reference(query)

    candidates = []

    for doc in chunks:
        rule_score, reasons, matched_keywords = calculate_rule_score(doc, query, question_ref)

        if rule_score > 0:
            cloned_doc = Document(
                page_content=doc.page_content,
                metadata=deepcopy(doc.metadata),
            )
            cloned_doc.metadata["_rule_score"] = round(rule_score, 4)
            cloned_doc.metadata["_rule_reasons"] = reasons
            cloned_doc.metadata["_matched_keywords"] = matched_keywords

            candidates.append((cloned_doc, rule_score))

    candidates.sort(key=lambda x: x[1], reverse=True)

    return candidates[:top_n], question_ref


# =========================
# 向量检索
# =========================

def vector_retrieve(vector_db, query, top_n=HYBRID_VECTOR_TOP_N):
    """
    调用 Chroma 向量检索。
    Chroma 返回的 score 通常是距离分数，越小越相关。
    """
    results = vector_db.similarity_search_with_score(query, k=top_n)

    candidates = []

    for doc, distance in results:
        cloned_doc = Document(
            page_content=doc.page_content,
            metadata=deepcopy(doc.metadata),
        )
        cloned_doc.metadata["_vector_distance"] = round(float(distance), 4)

        # 把距离转成 0-1 左右的相似度，越大越相关
        vector_similarity = 1.0 / (1.0 + float(distance))
        cloned_doc.metadata["_vector_similarity"] = round(vector_similarity, 4)

        candidates.append((cloned_doc, vector_similarity))

    return candidates


# =========================
# 文档唯一键，用于去重
# =========================

def get_doc_key(doc):
    metadata = doc.metadata or {}

    return (
        metadata.get("source", ""),
        metadata.get("file_type", ""),
        metadata.get("location", ""),
        metadata.get("chunk_id", ""),
    )


def build_retrieval_explanation(
    doc,
    question_ref,
    vector_similarity,
    rule_score,
    normalized_rule_score,
    hybrid_score,
    vector_weight,
    rule_weight,
    retrieval_methods,
):
    metadata = doc.metadata or {}

    return {
        "question_ref": question_ref,
        "method": "+".join(retrieval_methods),
        "matched_keywords": metadata.get("_matched_keywords", []),
        "vector": {
            "distance": metadata.get("_vector_distance", ""),
            "similarity": round(vector_similarity, 4),
        },
        "rule": {
            "score": round(rule_score, 4),
            "normalized_score": round(normalized_rule_score, 4),
            "reasons": metadata.get("_rule_reasons", []),
        },
        "hybrid": {
            "score": round(hybrid_score, 4),
            "weights": {
                "vector": vector_weight,
                "rule": rule_weight,
            },
        },
    }


# =========================
# 混合检索
# =========================

def hybrid_retrieve(vector_db, chunks, query, top_k, original_query=None):
    """
    混合检索入口。

    返回格式仍然保持：
    [
        (Document, hybrid_score),
        (Document, hybrid_score)
    ]

    hybrid_score 越高，表示综合排序越靠前。
    """
    rule_query = query

    if original_query and original_query != query:
        rule_query = f"{original_query}\n{query}"

    rule_candidates, question_ref = rule_retrieve(
        chunks=chunks,
        query=rule_query,
        top_n=HYBRID_RULE_TOP_N,
    )

    vector_candidates = vector_retrieve(
        vector_db=vector_db,
        query=query,
        top_n=HYBRID_VECTOR_TOP_N,
    )

    has_question_ref = (
        question_ref.get("question_type") is not None
        or question_ref.get("question_number") is not None
        or question_ref.get("section_ref") is not None
    )

    if has_question_ref:
        vector_weight = HYBRID_VECTOR_WEIGHT_WITH_REF
        rule_weight = HYBRID_RULE_WEIGHT_WITH_REF
    else:
        vector_weight = HYBRID_VECTOR_WEIGHT_NORMAL
        rule_weight = HYBRID_RULE_WEIGHT_NORMAL

    merged = {}

    # 先加入向量检索结果
    for doc, vector_similarity in vector_candidates:
        key = get_doc_key(doc)

        if key not in merged:
            merged[key] = {
                "doc": doc,
                "vector_similarity": 0.0,
                "rule_score": 0.0,
                "from_vector": False,
                "from_rule": False,
            }

        merged[key]["vector_similarity"] = max(
            merged[key]["vector_similarity"],
            vector_similarity,
        )
        merged[key]["from_vector"] = True

    # 再加入规则检索结果
    for doc, rule_score in rule_candidates:
        key = get_doc_key(doc)

        if key not in merged:
            merged[key] = {
                "doc": doc,
                "vector_similarity": 0.0,
                "rule_score": 0.0,
                "from_vector": False,
                "from_rule": False,
            }

        merged[key]["rule_score"] = max(
            merged[key]["rule_score"],
            rule_score,
        )
        merged[key]["from_rule"] = True

        # 保留规则原因
        merged[key]["doc"].metadata["_rule_score"] = doc.metadata.get("_rule_score", 0)
        merged[key]["doc"].metadata["_rule_reasons"] = doc.metadata.get("_rule_reasons", [])
        merged[key]["doc"].metadata["_matched_keywords"] = doc.metadata.get("_matched_keywords", [])

    # 规则分数归一化，避免数值过大
    max_rule_score = max(
        [item["rule_score"] for item in merged.values()] or [1.0]
    )

    if max_rule_score <= 0:
        max_rule_score = 1.0

    final_results = []

    for item in merged.values():
        doc = item["doc"]

        vector_similarity = item["vector_similarity"]
        rule_score = item["rule_score"]
        normalized_rule_score = rule_score / max_rule_score

        hybrid_score = (
            vector_weight * vector_similarity
            + rule_weight * normalized_rule_score
        )

        retrieval_methods = []

        if item["from_vector"]:
            retrieval_methods.append("vector")

        if item["from_rule"]:
            retrieval_methods.append("rule")

        doc.metadata["_retrieval_method"] = "+".join(retrieval_methods)
        doc.metadata["_hybrid_score"] = round(hybrid_score, 4)
        doc.metadata["_normalized_rule_score"] = round(normalized_rule_score, 4)
        doc.metadata["_question_ref"] = question_ref
        doc.metadata["_retrieval_explanation"] = build_retrieval_explanation(
            doc=doc,
            question_ref=question_ref,
            vector_similarity=vector_similarity,
            rule_score=rule_score,
            normalized_rule_score=normalized_rule_score,
            hybrid_score=hybrid_score,
            vector_weight=vector_weight,
            rule_weight=rule_weight,
            retrieval_methods=retrieval_methods,
        )

        final_results.append((doc, hybrid_score))

    final_results.sort(key=lambda x: x[1], reverse=True)

    return final_results[:top_k]
