#!/usr/bin/env python3
"""Collect public hot lists and render crawlable Markdown topic pages."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import html
import json
import random
import re
import string
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable


OWNER = "vlo808155"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0 Safari/537.36"
)
TIME_ZONE = timezone(timedelta(hours=8), name="Asia/Shanghai")
MINIMUM_ITEMS = 100
EXTERNAL_LINK_COUNT = 50
CONTENT_SCHEMA_VERSION = "5"

REPOSITORY_TOPICS: dict[str, list[tuple[str, str]]] = {
    "hua-she-tian-zu": [
        ("hua-she-tian-zu", "画蛇添足"),
        ("yi-xin-yi-yi", "一心一意"),
        ("san-xin-er-yi", "三心二意"),
        ("si-hai-wei-jia", "四海为家"),
        ("wu-gu-feng-deng", "五谷丰登"),
        ("liu-shen-wu-zhu", "六神无主"),
        ("qi-shang-ba-xia", "七上八下"),
        ("ba-mian-ling-long", "八面玲珑"),
        ("jiu-niu-yi-mao", "九牛一毛"),
        ("shi-quan-shi-mei", "十全十美"),
        ("bai-fa-bai-zhong", "百发百中"),
        ("qian-jun-wan-ma", "千军万马"),
        ("wan-zi-qian-hong", "万紫千红"),
        ("niao-yu-hua-xiang", "鸟语花香"),
        ("shan-qing-shui-xiu", "山清水秀"),
        ("feng-he-ri-li", "风和日丽"),
        ("chun-nuan-hua-kai", "春暖花开"),
        ("qiu-gao-qi-shuang", "秋高气爽"),
        ("bing-tian-xue-di", "冰天雪地"),
        ("ri-xin-yue-yi", "日新月异"),
    ],
    "shou-zhu-dai-tu": [
        ("shou-zhu-dai-tu", "守株待兔"),
        ("wang-mei-zhi-ke", "望梅止渴"),
        ("wen-ji-qi-wu", "闻鸡起舞"),
        ("wo-xin-chang-dan", "卧薪尝胆"),
        ("po-fu-chen-zhou", "破釜沉舟"),
        ("bei-shui-yi-zhan", "背水一战"),
        ("zhi-shang-tan-bing", "纸上谈兵"),
        ("wei-wei-jiu-zhao", "围魏救赵"),
        ("wan-bi-gui-zhao", "完璧归赵"),
        ("fu-jing-qing-zui", "负荆请罪"),
        ("mao-sui-zi-jian", "毛遂自荐"),
        ("san-gu-mao-lu", "三顾茅庐"),
        ("cao-mu-jie-bing", "草木皆兵"),
        ("feng-sheng-he-li", "风声鹤唳"),
        ("ru-huo-ru-tu", "如火如荼"),
        ("yi-gu-zuo-qi", "一鼓作气"),
        ("yi-zi-qian-jin", "一字千金"),
        ("yi-fan-feng-shun", "一帆风顺"),
        ("yi-ming-jing-ren", "一鸣惊人"),
        ("yi-jian-shuang-diao", "一箭双雕"),
    ],
    "ke-zhou-qiu-jian": [
        ("ke-zhou-qiu-jian", "刻舟求剑"),
        ("yan-er-dao-ling", "掩耳盗铃"),
        ("nan-yuan-bei-zhe", "南辕北辙"),
        ("mai-du-huan-zhu", "买椟还珠"),
        ("ye-gong-hao-long", "叶公好龙"),
        ("lan-yu-chong-shu", "滥竽充数"),
        ("zi-xiang-mao-dun", "自相矛盾"),
        ("bei-gong-she-ying", "杯弓蛇影"),
        ("jing-gong-zhi-niao", "惊弓之鸟"),
        ("hu-jia-hu-wei", "狐假虎威"),
        ("yu-mu-hun-zhu", "鱼目混珠"),
        ("dong-shi-xiao-pin", "东施效颦"),
        ("han-dan-xue-bu", "邯郸学步"),
        ("qi-ren-you-tian", "杞人忧天"),
        ("chao-san-mu-si", "朝三暮四"),
        ("dui-niu-tan-qin", "对牛弹琴"),
        ("mang-ren-mo-xiang", "盲人摸象"),
        ("yuan-mu-qiu-yu", "缘木求鱼"),
        ("sha-ji-qu-luan", "杀鸡取卵"),
        ("yin-zhen-zhi-ke", "饮鸩止渴"),
    ],
    "wang-yang-bu-lao": [
        ("wang-yang-bu-lao", "亡羊补牢"),
        ("xuan-liang-ci-gu", "悬梁刺股"),
        ("zao-bi-tou-guang", "凿壁偷光"),
        ("nang-ying-ying-xue", "囊萤映雪"),
        ("cheng-men-li-xue", "程门立雪"),
        ("shou-bu-shi-juan", "手不释卷"),
        ("xue-fu-wu-che", "学富五车"),
        ("bo-wen-qiang-ji", "博闻强记"),
        ("wen-gu-zhi-xin", "温故知新"),
        ("ju-yi-fan-san", "举一反三"),
        ("rong-hui-guan-tong", "融会贯通"),
        ("ji-si-guang-yi", "集思广益"),
        ("qu-chang-bu-duan", "取长补短"),
        ("jing-yi-qiu-jing", "精益求精"),
        ("jiao-ta-shi-di", "脚踏实地"),
        ("shi-shi-qiu-shi", "实事求是"),
        ("chi-zhi-yi-heng", "持之以恒"),
        ("jian-ren-bu-ba", "坚韧不拔"),
        ("zi-qiang-bu-xi", "自强不息"),
        ("fen-fa-tu-qiang", "奋发图强"),
    ],
    "jing-di-zhi-wa": [
        ("jing-di-zhi-wa", "井底之蛙"),
        ("hai-kuo-tian-kong", "海阔天空"),
        ("gao-zhan-yuan-zhu", "高瞻远瞩"),
        ("xiong-you-cheng-zhu", "胸有成竹"),
        ("yun-chou-wei-wo", "运筹帷幄"),
        ("shen-mou-yuan-lv", "深谋远虑"),
        ("ming-cha-qiu-hao", "明察秋毫"),
        ("jian-wei-zhi-zhu", "见微知著"),
        ("du-ju-hui-yan", "独具慧眼"),
        ("bie-ju-jiang-xin", "别具匠心"),
        ("qiao-duo-tian-gong", "巧夺天工"),
        ("gui-fu-shen-gong", "鬼斧神工"),
        ("jin-shang-tian-hua", "锦上添花"),
        ("hua-long-dian-jing", "画龙点睛"),
        ("miao-bi-sheng-hua", "妙笔生花"),
        ("sheng-dong-huo-po", "生动活泼"),
        ("xu-xu-ru-sheng", "栩栩如生"),
        ("huo-ling-huo-xian", "活灵活现"),
        ("you-sheng-you-se", "有声有色"),
        ("yin-ren-ru-sheng", "引人入胜"),
    ],
}


@dataclass(frozen=True)
class HotItem:
    source: str
    title: str
    summary: str
    url: str
    rank: int
    score: str = ""
    category: str = ""


def clean_text(value: Any, limit: int = 300) -> str:
    if value is None:
        return ""
    text = html.unescape(re.sub(r"<[^>]*>", " ", str(value)))
    text = re.sub(r"\s+", " ", text).strip(" #\t\r\n")
    return text[:limit].rstrip()


def fetch_json(url: str, referer: str) -> Any:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json,text/plain,*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.6",
            "Referer": referer,
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def default_summary(title: str, source: str, rank: int) -> str:
    return (
        f'“{title}”目前位于{source}热门榜单第 {rank} 位。'
        "榜单数据会随平台热度变化持续更新，事件详情与后续进展请以来源页面为准。"
    )


def walk_dicts(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_dicts(child)


def collect_baidu() -> list[HotItem]:
    data = fetch_json(
        "https://top.baidu.com/api/board?platform=pc&tab=realtime",
        "https://top.baidu.com/board?tab=realtime",
    )
    items: list[HotItem] = []
    for node in walk_dicts(data):
        title = clean_text(node.get("word"), 100)
        if not title or node.get("isTop") is True:
            continue
        rank = int(node.get("index") or len(items) + 1)
        url = clean_text(node.get("url"), 500) or (
            "https://www.baidu.com/s?wd=" + urllib.parse.quote(title)
        )
        summary = clean_text(node.get("desc") or node.get("summary"), 280)
        items.append(
            HotItem(
                source="百度热搜",
                title=title,
                summary=summary or default_summary(title, "百度热搜", rank),
                url=url,
                rank=rank,
                score=clean_text(node.get("hotScore") or node.get("hot_score"), 40),
                category=clean_text(node.get("labelTagName") or node.get("newHotName"), 30),
            )
        )
    return deduplicate(items)[:50]


def collect_weibo() -> list[HotItem]:
    data = fetch_json(
        "https://weibo.com/ajax/statuses/hot_band",
        "https://weibo.com/hot/search",
    )
    rows = data.get("data", {}).get("band_list", [])
    items: list[HotItem] = []
    for row in rows:
        if not isinstance(row, dict) or int(row.get("is_ad") or 0) == 1:
            continue
        title = clean_text(row.get("note") or row.get("word"), 100)
        if not title:
            continue
        rank = len(items) + 1
        query = clean_text(row.get("word_scheme") or title, 120)
        url = "https://s.weibo.com/weibo?q=" + urllib.parse.quote(query)
        category = clean_text(row.get("category") or row.get("icon_desc"), 30)
        items.append(
            HotItem(
                source="微博热搜",
                title=title,
                summary=default_summary(title, "微博热搜", rank),
                url=url,
                rank=rank,
                score=clean_text(row.get("raw_hot") or row.get("num"), 40),
                category=category,
            )
        )
    return deduplicate(items)[:50]


def collect_toutiao() -> list[HotItem]:
    data = fetch_json(
        "https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc",
        "https://www.toutiao.com/",
    )
    rows = data.get("data", []) if isinstance(data, dict) else []
    items: list[HotItem] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        title = clean_text(row.get("Title") or row.get("QueryWord"), 100)
        if not title:
            continue
        rank = len(items) + 1
        items.append(
            HotItem(
                source="今日头条热榜",
                title=title,
                summary=default_summary(title, "今日头条热榜", rank),
                url=clean_text(row.get("Url"), 500)
                or "https://so.toutiao.com/search?keyword=" + urllib.parse.quote(title),
                rank=rank,
                score=clean_text(row.get("HotValue"), 40),
                category=clean_text(row.get("LabelDesc") or row.get("Label"), 30),
            )
        )
    return deduplicate(items)[:50]


def collect_zhihu() -> list[HotItem]:
    data = fetch_json(
        "https://api.zhihu.com/topstory/hot-lists/total?limit=50",
        "https://www.zhihu.com/hot",
    )
    rows = data.get("data", []) if isinstance(data, dict) else []
    items: list[HotItem] = []
    for row in rows:
        target = row.get("target", {}) if isinstance(row, dict) else {}
        title = clean_text(target.get("title"), 100)
        if not title:
            continue
        rank = len(items) + 1
        question_id = target.get("id")
        url = (
            f"https://www.zhihu.com/question/{question_id}"
            if question_id
            else "https://www.zhihu.com/hot"
        )
        excerpt = clean_text(target.get("excerpt"), 280)
        items.append(
            HotItem(
                source="知乎热榜",
                title=title,
                summary=excerpt or default_summary(title, "知乎热榜", rank),
                url=url,
                rank=rank,
                score=clean_text(row.get("detail_text"), 40),
                category="问答",
            )
        )
    return deduplicate(items)[:50]


def collect_bilibili() -> list[HotItem]:
    data = fetch_json(
        "https://api.bilibili.com/x/web-interface/popular?ps=50&pn=1",
        "https://www.bilibili.com/v/popular/all",
    )
    if not isinstance(data, dict) or data.get("code") != 0:
        raise RuntimeError(f"Bilibili API rejected the request: {data.get('code') if isinstance(data, dict) else 'invalid response'}")
    rows = data.get("data", {}).get("list", [])
    items: list[HotItem] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        title = clean_text(row.get("title"), 100)
        if not title:
            continue
        rank = len(items) + 1
        bvid = clean_text(row.get("bvid"), 40)
        summary = clean_text(row.get("desc"), 280)
        score = clean_text((row.get("stat") or {}).get("view"), 40)
        items.append(
            HotItem(
                source="哔哩哔哩热门",
                title=title,
                summary=summary or default_summary(title, "哔哩哔哩热门", rank),
                url=clean_text(row.get("short_link_v2"), 500)
                or (f"https://www.bilibili.com/video/{bvid}" if bvid else "https://www.bilibili.com/v/popular/all"),
                rank=rank,
                score=score,
                category=clean_text(row.get("tname"), 30),
            )
        )
    return deduplicate(items)[:50]


def deduplicate(items: Iterable[HotItem]) -> list[HotItem]:
    seen: set[str] = set()
    result: list[HotItem] = []
    for item in items:
        key = re.sub(r"\W+", "", item.title, flags=re.UNICODE).casefold()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def collect_all() -> tuple[list[HotItem], dict[str, str], dict[str, int]]:
    collectors: list[tuple[str, Callable[[], list[HotItem]]]] = [
        ("百度热搜", collect_baidu),
        ("微博热搜", collect_weibo),
        ("今日头条热榜", collect_toutiao),
        ("知乎热榜", collect_zhihu),
        ("哔哩哔哩热门", collect_bilibili),
    ]
    results: dict[str, list[HotItem]] = {}
    errors: dict[str, str] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(collectors)) as executor:
        futures = {executor.submit(func): name for name, func in collectors}
        for future in concurrent.futures.as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception as exc:  # A failed source must not stop healthy sources.
                results[name] = []
                errors[name] = clean_text(exc, 240)

    ordered: list[HotItem] = []
    seen_titles: set[str] = set()
    max_length = max((len(items) for items in results.values()), default=0)
    for index in range(max_length):
        for name, _ in collectors:
            source_items = results.get(name, [])
            if index >= len(source_items):
                continue
            item = source_items[index]
            key = re.sub(r"\W+", "", item.title, flags=re.UNICODE).casefold()
            if key in seen_titles:
                continue
            seen_titles.add(key)
            ordered.append(item)

    counts = {name: len(results.get(name, [])) for name, _ in collectors}
    if len(ordered) < MINIMUM_ITEMS:
        raise RuntimeError(
            f"Only {len(ordered)} unique hot items were collected; refusing to overwrite 100 pages. "
            f"Source counts: {counts}; errors: {errors}"
        )
    return ordered[:MINIMUM_ITEMS], errors, counts


def load_external_link_templates(repo_dir: Path) -> list[tuple[str, str]]:
    path = repo_dir / "url.txt"
    if not path.is_file():
        raise FileNotFoundError(f"External link template file not found: {path}")
    templates: list[tuple[str, str]] = []
    for raw_line in path.read_text("utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        tag = ""
        template = line
        if "|" in line:
            tag, template = (part.strip() for part in line.split("|", 1))
        if not re.match(r"^https?://", template, re.IGNORECASE):
            template = "https://" + template
        if re.match(r"^https?://[^\s]+$", template, re.IGNORECASE):
            templates.append((clean_text(tag, 30), template))
    if not templates:
        raise ValueError(f"No usable external link templates in {path}")
    return templates


def expand_external_template(template: str, rng: random.Random) -> str:
    def digits(match: re.Match[str]) -> str:
        return "".join(rng.choice(string.digits) for _ in range(int(match.group(1))))

    def lowercase(match: re.Match[str]) -> str:
        return "".join(rng.choice(string.ascii_lowercase) for _ in range(int(match.group(1))))

    value = re.sub(r"\{随机数字=(\d{1,3})\}", digits, template)
    return re.sub(r"\{随机小写=(\d{1,3})\}", lowercase, value)


def generate_external_links(
    slug: str,
    title: str,
    tags: list[str],
    templates: list[tuple[str, str]],
) -> list[tuple[str, str]]:
    matching = [entry for entry in templates if not entry[0] or entry[0] in tags]
    pool = matching or templates
    seed_material = slug + "\n" + "\n".join(f"{tag}|{url}" for tag, url in pool)
    seed = int.from_bytes(hashlib.sha256(seed_material.encode("utf-8")).digest()[:8], "big")
    rng = random.Random(seed)
    links: list[tuple[str, str]] = []
    seen: set[str] = set()
    attempts = 0
    while len(links) < EXTERNAL_LINK_COUNT and attempts < EXTERNAL_LINK_COUNT * 20:
        attempts += 1
        _template_tag, template = rng.choice(pool)
        url = expand_external_template(template, rng)
        if url in seen:
            continue
        seen.add(url)
        links.append((title, url))
    if len(links) != EXTERNAL_LINK_COUNT:
        raise ValueError(f"Could not generate {EXTERNAL_LINK_COUNT} unique external links for {slug}")
    return links


def markdown_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("<", "&lt;").replace(">", "&gt;")


def render_article_body(item: HotItem) -> str:
    score_text = f"，公开热度指标为 {item.score}" if item.score else ""
    category_text = f"，榜单分类为“{item.category}”" if item.category else ""
    signal_paragraph = (
        f"根据{item.source}当前公开榜单，“{item.title}”位列第 {item.rank} 位"
        f"{score_text}{category_text}。这些数据说明该话题正在获得集中关注，"
        "但榜单位置只代表阶段性热度，不等同于对事件事实或观点的确认。"
    )
    generated = item.summary == default_summary(item.title, item.source, item.rank)
    if generated:
        source_paragraph = (
            f"{item.source}本次榜单数据只提供了热点标题和热度信息，没有提供可独立发布的完整正文。"
            "本页因此保留来源边界，不根据标题补写未经证实的时间、人物、地点或事件经过。"
        )
    else:
        source_paragraph = f"来源公开摘要显示：{item.summary}"
    follow_up = (
        "阅读这一话题时，可继续关注原始页面中的最新报道、当事方回应和权威机构发布。"
        "若榜单排名、公开摘要或来源信息发生变化，本页会在后续采集周期中同步更新。"
    )
    return "\n\n".join(markdown_text(value) for value in [signal_paragraph, source_paragraph, follow_up])


def item_fingerprint(item: HotItem) -> str:
    payload = "\n".join(
        [item.source, item.title, item.summary, item.url, str(item.rank), item.score, item.category]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]


def page_fingerprint(
    rows: list[tuple[str, str, HotItem]],
    index: int,
    templates: list[tuple[str, str]],
    all_items: list[HotItem],
) -> str:
    linked_indexes = [(index - 1) % len(rows)] + [
        (index + step) % len(rows) for step in range(0, 5)
    ]
    payload = "\n".join(
        f"{rows[row_index][0]}:{item_fingerprint(rows[row_index][2])}"
        for row_index in linked_indexes
    )
    payload += "\n" + "\n".join(f"{tag}|{url}" for tag, url in templates)
    payload += "\n" + "\n".join(
        f"{repo}:{slug}:{item_fingerprint(item)}"
        for repo, slug, item in cross_repository_items(all_items, index)
    )
    payload += "\ncontent-schema:" + CONTENT_SCHEMA_VERSION
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]


def cross_repository_items(
    items: list[HotItem],
    index: int,
) -> list[tuple[str, str, HotItem]]:
    result: list[tuple[str, str, HotItem]] = []
    offset = 0
    for repo, topics in REPOSITORY_TOPICS.items():
        topic_index = (index + len(topics) // 2) % len(topics)
        slug = topics[topic_index][0]
        result.append((repo, slug, items[offset + topic_index]))
        offset += len(topics)
    return result


def existing_fingerprint(path: Path) -> str:
    if not path.is_file():
        return ""
    content = path.read_text("utf-8")
    match = re.search(r'<!--\s*content-fingerprint:\s*([0-9a-f]{20})\s*-->', content)
    if not match:
        match = re.search(r'^content_fingerprint:\s*"?([0-9a-f]{20})"?\s*$', content, re.MULTILINE)
    return match.group(1) if match else ""


def render_topic(
    rows: list[tuple[str, str, HotItem]],
    index: int,
    updated_at: str,
    templates: list[tuple[str, str]],
    all_items: list[HotItem],
) -> str:
    slug, idiom, item = rows[index]
    fingerprint = page_fingerprint(rows, index, templates, all_items)
    tags = [item.source, "实时热搜", "热点资讯"]
    if item.category and item.category not in tags:
        tags.append(item.category)
    tag_text = " ".join(f"`{markdown_text(tag)}`" for tag in tags)
    related_rows = [rows[(index + step) % len(rows)] for step in range(1, 5)]
    related_links = "\n".join(
        f"- [{markdown_text(related_item.title)}]({related_slug}.md)"
        for related_slug, _related_idiom, related_item in related_rows
    )
    repository_links = "\n".join(
        f"- [{markdown_text(target_item.title)}]"
        f"(https://github.com/{name_with_owner}/blob/main/{target_slug}.md)"
        for target_repo, target_slug, target_item in cross_repository_items(all_items, index)
        for name_with_owner in [f"{OWNER}/{target_repo}"]
    )
    external_links = generate_external_links(slug, item.title, tags, templates)
    external_link_lines = "\n".join(
        f"- [{markdown_text(anchor)}]({url})" for anchor, url in external_links
    )
    status_parts = [
        f"来源：{markdown_text(item.source)}",
        f"排名：第 {item.rank} 位",
    ]
    if item.score:
        status_parts.append(f"热度：{markdown_text(item.score)}")
    if item.category:
        status_parts.append(f"分类：{markdown_text(item.category)}")
    status_parts.append(f"更新：{updated_at}")
    return (
        "[热点索引](README.md)\n\n"
        f"# {markdown_text(item.title)}\n\n"
        f"> {' · '.join(status_parts)}\n\n"
        "## 热点正文\n\n"
        f"{render_article_body(item)}\n\n"
        "## 相关标签\n\n"
        f"{tag_text}\n\n"
        "## 相关热点\n\n"
        f"{related_links}\n\n"
        "## 站内推荐\n\n"
        f"{repository_links}\n\n"
        "## 相关资讯\n\n"
        "<details>\n"
        f"<summary>展开更多相关内容</summary>\n\n"
        f"{external_link_lines}\n\n"
        "</details>\n\n"
        "## 原始来源\n\n"
        f"- [{markdown_text(item.title)}]({item.url})\n\n"
        "完整信息及后续变化请以原始来源为准。\n\n"
        f"<!-- content-fingerprint: {fingerprint} -->\n"
    )


def render_readme(repo: str, rows: list[tuple[str, str, HotItem]], updated_at: str) -> str:
    table = []
    for index, (slug, _idiom, item) in enumerate(rows, start=1):
        title = markdown_text(item.title).replace("|", "\\|")
        table.append(
            f"| {index} | [{title}]({slug}.md) | {item.source} |"
        )
    return (
        f"# {repo}\n\n"
        "实时热点内容索引。页面采集公开榜单的标题、摘要、排名与来源链接，"
        "每 10 分钟检查一次，仅在榜单内容变化时提交更新。\n\n"
        f"最后更新：{updated_at}\n\n"
        "| 序号 | 热点标题 | 来源 |\n"
        "| ---: | --- | --- |\n"
        + "\n".join(table)
        + "\n\n"
        "## 热点仓库导航\n\n"
        + "\n".join(
            f"- [{name} 热点内容](https://github.com/{OWNER}/{name}/blob/main/{topics[0][0]}.md)"
            for name, topics in REPOSITORY_TOPICS.items()
        )
        + "\n\n"
        "## 数据来源\n\n"
        "- [百度热搜](https://top.baidu.com/board?tab=realtime)\n"
        "- [微博热搜](https://weibo.com/hot/search)\n"
        "- [今日头条热榜](https://www.toutiao.com/)\n"
        "- [知乎热榜](https://www.zhihu.com/hot)\n"
        "- [哔哩哔哩热门](https://www.bilibili.com/v/popular/all)\n\n"
        "本站不复制完整第三方文章。热点页面中的内容用于榜单索引，详情请访问原始来源。\n"
    )


def validate_topic_map() -> None:
    if len(REPOSITORY_TOPICS) != 5:
        raise ValueError("Exactly five repositories are required")
    all_slugs: list[str] = []
    for repo, topics in REPOSITORY_TOPICS.items():
        if len(topics) != 20:
            raise ValueError(f"{repo} has {len(topics)} topics instead of 20")
        for slug, idiom in topics:
            if not re.fullmatch(r"[a-z]+(?:-[a-z]+){3}", slug):
                raise ValueError(f"Invalid four-syllable slug: {slug}")
            if len(idiom) != 4:
                raise ValueError(f"Idiom must contain four characters: {idiom}")
            all_slugs.append(slug)
    if len(all_slugs) != len(set(all_slugs)):
        raise ValueError("Pinyin slugs must be globally unique")


def update_repository(repo_dir: Path, repo: str, items: list[HotItem], updated_at: str) -> dict[str, Any]:
    if repo not in REPOSITORY_TOPICS:
        raise ValueError(f"Unknown repository: {repo}")
    if not (repo_dir / ".git").exists():
        raise FileNotFoundError(f"Repository checkout not found: {repo_dir}")

    offset = 0
    for name, topics in REPOSITORY_TOPICS.items():
        if name == repo:
            break
        offset += len(topics)

    rows = [
        (slug, idiom, items[offset + index])
        for index, (slug, idiom) in enumerate(REPOSITORY_TOPICS[repo])
    ]
    templates = load_external_link_templates(repo_dir)
    changed_files: list[str] = []
    for index, (slug, _idiom, item) in enumerate(rows):
        path = repo_dir / f"{slug}.md"
        current = path.read_text("utf-8") if path.is_file() else ""
        has_navigation = "## 站内推荐" in current and "## 相关资讯" in current
        if existing_fingerprint(path) == page_fingerprint(rows, index, templates, items) and has_navigation:
            continue
        path.write_text(render_topic(rows, index, updated_at, templates, items), encoding="utf-8", newline="\n")
        changed_files.append(path.name)

    readme = repo_dir / "README.md"
    if changed_files or not readme.is_file():
        readme.write_text(render_readme(repo, rows, updated_at), encoding="utf-8", newline="\n")
        changed_files.append(readme.name)
    return {"changed": len(changed_files), "files": changed_files}


def update_workspace(workspace: Path, items: list[HotItem]) -> dict[str, Any]:
    updated_at = datetime.now(TIME_ZONE).isoformat(timespec="seconds")
    return {
        repo: update_repository(workspace / repo, repo, items, updated_at)
        for repo in REPOSITORY_TOPICS
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    targets = parser.add_mutually_exclusive_group(required=True)
    targets.add_argument(
        "--workspace",
        type=Path,
        help="Directory containing the five repository checkouts",
    )
    targets.add_argument(
        "--repository",
        type=Path,
        help="Single repository checkout to update",
    )
    parser.add_argument(
        "--repository-name",
        choices=REPOSITORY_TOPICS,
        help="Repository name used with --repository",
    )
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    if args.repository and not args.repository_name:
        parser.error("--repository-name is required with --repository")
    if args.workspace and args.repository_name:
        parser.error("--repository-name can only be used with --repository")
    return args


def main() -> int:
    args = parse_args()
    validate_topic_map()
    if args.validate_only:
        print(json.dumps({"repositories": 5, "topics": 100}, ensure_ascii=False))
        return 0
    items, errors, counts = collect_all()
    if args.repository:
        updated_at = datetime.now(TIME_ZONE).isoformat(timespec="seconds")
        changes = {
            args.repository_name: update_repository(
                args.repository.resolve(), args.repository_name, items, updated_at
            )
        }
    else:
        changes = update_workspace(args.workspace.resolve(), items)
    print(
        json.dumps(
            {
                "collected": len(items),
                "source_counts": counts,
                "source_errors": errors,
                "repositories": changes,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise
