"""使用纯 Python（标准库）生成中文词云 SVG 图片。"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import html
import math
import random
import re

INPUT_FILE = Path("honors.txt")
OUTPUT_FILE = Path("honors_wordcloud.svg")
CANVAS_WIDTH = 1600
CANVAS_HEIGHT = 1000
MAX_WORDS = 120
MIN_FONT = 14
MAX_FONT = 96
RANDOM_SEED = 2026

# 针对“荣誉/资质”文本场景的关键词词典（可按需扩展）
KEYWORDS = [
    "企业技术中心", "工程技术研究中心", "企业研究院", "高新技术企业", "科技进步奖", "技术创新奖", "单项冠军",
    "瞪羚企业", "独角兽企业", "专精特新", "绿色工厂", "知识产权", "示范企业", "示范单位", "工业设计中心",
    "制造业", "智能制造", "科学技术奖", "技术中心", "研究中心", "重点实验室", "博士后科研工作站", "隐形冠军",
    "百强企业", "创新企业", "领军企业", "质量检验检测中心", "品牌", "创新", "科技", "工业",
    "浙江省", "江苏省", "广东省", "上海市", "苏州市", "无锡市", "重庆市", "山东省", "湖北省", "安徽省",
]

STOPWORDS = {
    "企业", "年度", "有限公司", "公司", "中国", "国家", "省", "市", "年", "第", "和", "等", "类",
    "被", "为", "及", "项", "计划", "示范", "中心", "认定", "入选", "获评", "获", "以及", "荣获", "先后",
}


def tokenize(text: str) -> list[str]:
    """优先按业务关键词抽取；不足时回退到短语切分。"""
    compact = re.sub(r"\s+", "", text)
    tokens: list[str] = []

    for word in KEYWORDS:
        count = compact.count(word)
        if count > 0:
            tokens.extend([word] * count)

    if len(tokens) >= 60:
        return tokens

    # 回退：从中文短语中提取 2~8 字片段
    phrases = re.findall(r"[\u4e00-\u9fff]{2,}", text)
    for phrase in phrases:
        phrase = phrase.strip()
        if not phrase or phrase in STOPWORDS:
            continue
        if 2 <= len(phrase) <= 8:
            tokens.append(phrase)

    return tokens


def rects_overlap(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    return not (ax2 < bx1 or bx2 < ax1 or ay2 < by1 or by2 < ay1)


def estimate_text_bbox(x: float, y: float, word: str, font_size: int) -> tuple[float, float, float, float]:
    width = font_size * (0.56 * len(word) + 0.8)
    height = font_size * 1.05
    return (x, y - height, x + width, y)


def place_words(freq: list[tuple[str, int]]) -> list[tuple[str, int, float, float, str]]:
    """螺旋放置，尽量避免重叠。"""
    placed: list[tuple[str, int, float, float, str]] = []
    boxes: list[tuple[float, float, float, float]] = []
    center_x = CANVAS_WIDTH / 2
    center_y = CANVAS_HEIGHT / 2
    palette = ["#1565C0", "#2E7D32", "#EF6C00", "#6A1B9A", "#00838F", "#C62828", "#455A64"]

    max_count = freq[0][1]
    min_count = freq[-1][1]
    span = max(1, max_count - min_count)

    rng = random.Random(RANDOM_SEED)

    for idx, (word, count) in enumerate(freq):
        ratio = (count - min_count) / span
        font_size = int(MIN_FONT + ratio * (MAX_FONT - MIN_FONT))
        color = palette[idx % len(palette)]

        placed_ok = False
        for step in range(2600):
            angle = step * 0.35
            radius = 4 + 2.0 * angle
            x = center_x + radius * math.cos(angle) + rng.uniform(-6, 6)
            y = center_y + radius * math.sin(angle) + rng.uniform(-6, 6)

            bbox = estimate_text_bbox(x, y, word, font_size)
            x1, y1, x2, y2 = bbox
            if x1 < 10 or y1 < 10 or x2 > CANVAS_WIDTH - 10 or y2 > CANVAS_HEIGHT - 10:
                continue
            if any(rects_overlap(bbox, old) for old in boxes):
                continue

            boxes.append(bbox)
            placed.append((word, font_size, x, y, color))
            placed_ok = True
            break

        if not placed_ok:
            continue

    return placed


def build_svg(elements: list[tuple[str, int, float, float, str]]) -> str:
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_WIDTH}" height="{CANVAS_HEIGHT}" viewBox="0 0 {CANVAS_WIDTH} {CANVAS_HEIGHT}">',
        '<rect width="100%" height="100%" fill="#FFFFFF"/>',
        '<g font-family="Microsoft YaHei, PingFang SC, Noto Sans CJK SC, sans-serif">',
    ]
    for word, font_size, x, y, color in elements:
        safe_word = html.escape(word)
        lines.append(
            f'<text x="{x:.2f}" y="{y:.2f}" font-size="{font_size}" fill="{color}">{safe_word}</text>'
        )
    lines.append("</g>")
    lines.append("</svg>")
    return "\n".join(lines)


def generate_wordcloud(text: str) -> None:
    tokens = tokenize(text)
    freq = Counter(tokens).most_common(MAX_WORDS)
    if not freq:
        raise SystemExit("输入文本为空或过滤后无可用词语，无法生成词云。")

    elements = place_words(freq)
    svg = build_svg(elements)
    OUTPUT_FILE.write_text(svg, encoding="utf-8")


if __name__ == "__main__":
    raw_text = INPUT_FILE.read_text(encoding="utf-8")
    generate_wordcloud(raw_text)
    print(f"词云图已生成：{OUTPUT_FILE.resolve()}")
