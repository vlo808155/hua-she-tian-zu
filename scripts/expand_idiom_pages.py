#!/usr/bin/env python3
"""Expand the five repositories to 500 content Markdown files each."""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
import urllib.request
from pathlib import Path
from typing import Any

from update_hot_topics import (
    OWNER,
    REPOSITORY_TOPICS,
    USER_AGENT,
    clean_text,
    collect_all,
    generate_external_links,
    load_external_link_templates,
    markdown_text,
)


DATASET_URL = "https://raw.githubusercontent.com/pwxcoo/chinese-xinhua/master/data/idiom.json"
DATASET_PAGE = "https://github.com/pwxcoo/chinese-xinhua"
TARGET_CONTENT_FILES = 500


def fetch_dataset() -> list[dict[str, Any]]:
    request = urllib.request.Request(DATASET_URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def pinyin_slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.lower())
    ascii_value = "".join(char for char in normalized if not unicodedata.combining(char))
    parts = re.findall(r"[a-z]+", ascii_value)
    return "-".join(parts)


def select_idioms(dataset: list[dict[str, Any]]) -> dict[str, list[dict[str, str]]]:
    used_slugs = {
        slug
        for topics in REPOSITORY_TOPICS.values()
        for slug, _idiom in topics
    }
    used_words = {
        idiom
        for topics in REPOSITORY_TOPICS.values()
        for _slug, idiom in topics
    }
    needed_per_repo = TARGET_CONTENT_FILES - len(next(iter(REPOSITORY_TOPICS.values())))
    selected: list[dict[str, str]] = []
    for entry in dataset:
        word = clean_text(entry.get("word"), 20)
        slug = pinyin_slug(clean_text(entry.get("pinyin"), 100))
        explanation = clean_text(entry.get("explanation"), 1200)
        if not re.fullmatch(r"[\u4e00-\u9fff]{4}", word):
            continue
        if not re.fullmatch(r"[a-z]+(?:-[a-z]+){3}", slug):
            continue
        if word in used_words or slug in used_slugs or len(explanation) < 8:
            continue
        used_words.add(word)
        used_slugs.add(slug)
        selected.append(
            {
                "word": word,
                "slug": slug,
                "pinyin": clean_text(entry.get("pinyin"), 100),
                "explanation": explanation,
                "derivation": clean_text(entry.get("derivation"), 1200),
                "example": clean_text(entry.get("example"), 1200),
            }
        )
        if len(selected) == needed_per_repo * len(REPOSITORY_TOPICS):
            break
    required = needed_per_repo * len(REPOSITORY_TOPICS)
    if len(selected) != required:
        raise RuntimeError(f"Selected {len(selected)} idioms, expected {required}")
    return {
        repo: selected[index * needed_per_repo : (index + 1) * needed_per_repo]
        for index, repo in enumerate(REPOSITORY_TOPICS)
    }


def render_page(
    repo: str,
    index: int,
    entry: dict[str, str],
    allocations: dict[str, list[dict[str, str]]],
    hot_items: list[Any],
    templates: list[tuple[str, str]],
) -> str:
    related = [
        allocations[repo][(index + offset) % len(allocations[repo])]
        for offset in range(1, 5)
    ]
    related_links = "\n".join(
        f"- [{item['word']}]({item['slug']}.md)" for item in related
    )
    network_links = []
    for target_repo, entries in allocations.items():
        target = entries[(index + len(entries) // 2) % len(entries)]
        network_links.append(
            f"- [{target['word']}](https://github.com/{OWNER}/{target_repo}/blob/main/{target['slug']}.md)"
        )
    external_links = generate_external_links(
        entry["slug"],
        entry["word"],
        hot_items,
        ["四字成语", "成语释义", "热点资讯"],
        templates,
    )
    external_lines = "\n".join(
        f"- [{markdown_text(title)}]({url})" for title, url in external_links
    )
    derivation = (
        f"## 成语出处\n\n{markdown_text(entry['derivation'])}\n\n"
        if entry["derivation"]
        else ""
    )
    example = (
        f"## 使用示例\n\n{markdown_text(entry['example'])}\n\n"
        if entry["example"]
        else ""
    )
    return (
        "[内容索引](README.md)\n\n"
        f"# {entry['word']}\n\n"
        f"> 拼音：{entry['pinyin']}\n\n"
        "## 成语释义\n\n"
        f"{markdown_text(entry['explanation'])}\n\n"
        f"{derivation}"
        f"{example}"
        "## 相关成语\n\n"
        f"{related_links}\n\n"
        "## 站内推荐\n\n"
        + "\n".join(network_links)
        + "\n\n"
        "## 相关资讯\n\n"
        "<details>\n<summary>展开更多相关内容</summary>\n\n"
        f"{external_lines}\n\n"
        "</details>\n\n"
        "## 数据来源\n\n"
        f"- [chinese-xinhua 成语数据（MIT）]({DATASET_PAGE})\n"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workspace = args.workspace.resolve()
    dataset = fetch_dataset()
    allocations = select_idioms(dataset)
    hot_items, source_errors, source_counts = collect_all()
    summary: dict[str, Any] = {}
    for repo, entries in allocations.items():
        repo_dir = workspace / repo
        templates = load_external_link_templates(repo_dir)
        for index, entry in enumerate(entries):
            path = repo_dir / f"{entry['slug']}.md"
            path.write_text(
                render_page(repo, index, entry, allocations, hot_items, templates),
                encoding="utf-8",
                newline="\n",
            )
        notice = (
            "Idiom names, pinyin, explanations, derivations, and examples are derived from\n"
            "pwxcoo/chinese-xinhua, distributed under the MIT License:\n"
            f"{DATASET_PAGE}\n"
        )
        (repo_dir / "IDIOM_DATA_NOTICE.txt").write_text(notice, encoding="utf-8", newline="\n")
        content_count = len([path for path in repo_dir.glob("*.md") if path.name != "README.md"])
        summary[repo] = {"created": len(entries), "content_markdown": content_count}
    print(
        json.dumps(
            {
                "repositories": summary,
                "source_counts": source_counts,
                "source_errors": source_errors,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
