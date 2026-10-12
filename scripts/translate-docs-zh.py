#!/usr/bin/env python3
"""Translate docs/*.md to sibling *_zh.md files with a local Ollama model.

This is intentionally conservative:
- source English docs are never modified;
- fenced code blocks are copied unchanged;
- Markdown link targets are rewritten to *_zh.md only when that target exists.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.error
import urllib.request
from pathlib import Path


DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")


PROMPT = """你是技术文档翻译器。请将下面的 Markdown 原文完整翻译为简体中文。
只输出翻译后的 Markdown 正文，不要输出说明、提示词、前后引号或 Markdown 代码围栏。
不得总结、删减、扩写或改变顺序。保留标题层级、列表、表格、引用、空行和代码块。
保留所有代码、命令、文件路径、TOML/JSON/YAML 键、API 名称、URL、锚点、数字和单位。
链接目标保持原样，只翻译链接的可见文字。

原文开始
"""


FENCE_RE = re.compile(r"^(```|~~~)")
INLINE_LINK_RE = re.compile(r"\]\(([^)]+\.md)(#[^)]+)?\)")
REF_LINK_RE = re.compile(r"^(\s*\[[^\]]+\]:\s*)(\S+\.md)(#[^\s]+)?(\s*)$", re.MULTILINE)
INLINE_CODE_RE = re.compile(r"(`+)([^`\n]+?)(\1)")
URL_RE = re.compile(r"https?://[^\s)<]+")
LINK_TARGET_RE = re.compile(r"(\]\()([^)]+)(\))")


def split_fenced_blocks(text: str) -> list[tuple[str, str]]:
    parts: list[tuple[str, str]] = []
    buf: list[str] = []
    in_fence = False
    fence_marker = ""
    current_kind = "text"

    for line in text.splitlines(keepends=True):
        marker = FENCE_RE.match(line)
        if marker:
            marker_text = marker.group(1)
            if not in_fence:
                if buf:
                    parts.append((current_kind, "".join(buf)))
                    buf = []
                in_fence = True
                fence_marker = marker_text
                current_kind = "code"
            elif marker_text == fence_marker:
                buf.append(line)
                parts.append((current_kind, "".join(buf)))
                buf = []
                in_fence = False
                fence_marker = ""
                current_kind = "text"
                continue
        buf.append(line)

    if buf:
        parts.append((current_kind, "".join(buf)))
    return parts


def split_text_chunk(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    paragraphs = re.split(r"(\n\s*\n)", text)
    for part in paragraphs:
        part_len = len(part)
        if current and current_len + part_len > max_chars:
            chunks.append("".join(current))
            current = []
            current_len = 0
        if part_len > max_chars:
            lines = part.splitlines(keepends=True)
            for line in lines:
                if current and current_len + len(line) > max_chars:
                    chunks.append("".join(current))
                    current = []
                    current_len = 0
                current.append(line)
                current_len += len(line)
        else:
            current.append(part)
            current_len += part_len

    if current:
        chunks.append("".join(current))
    return chunks


def ollama_generate(model: str, prompt: str, retries: int = 3) -> str:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "top_p": 0.9,
            "num_predict": 8192,
        },
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            text = result.get("response", "")
            return cleanup_model_output(text)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            time.sleep(attempt * 2)
    raise RuntimeError(f"Ollama request failed after {retries} attempts: {last_error}")


def google_translate(text: str, retries: int = 3) -> str:
    protected, placeholders = protect_markdown_inline(text)
    params = urllib.parse.urlencode(
        {
            "client": "gtx",
            "sl": "en",
            "tl": "zh-CN",
            "dt": "t",
            "q": protected,
        }
    )
    url = f"https://translate.googleapis.com/translate_a/single?{params}"
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(url, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            translated = "".join(part[0] for part in data[0] if part and part[0])
            return restore_placeholders(translated, placeholders)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, IndexError) as exc:
            last_error = exc
            time.sleep(attempt * 2)
    raise RuntimeError(f"Google Translate request failed after {retries} attempts: {last_error}")


def protect_markdown_inline(text: str) -> tuple[str, dict[str, str]]:
    placeholders: dict[str, str] = {}

    def put(value: str) -> str:
        key = f"ZXQ{len(placeholders):04d}QXZ"
        placeholders[key] = value
        return key

    text = LINK_TARGET_RE.sub(lambda m: m.group(1) + put(m.group(2)) + m.group(3), text)
    text = URL_RE.sub(lambda m: put(m.group(0)), text)
    text = INLINE_CODE_RE.sub(lambda m: put(m.group(0)), text)
    return text, placeholders


def restore_placeholders(text: str, placeholders: dict[str, str]) -> str:
    for key, value in placeholders.items():
        variants = {
            key,
            key.lower(),
            key.replace("Q", " q "),
            key.replace("ZXQ", "ZX Q").replace("QXZ", "Q XZ"),
        }
        for variant in variants:
            text = text.replace(variant, value)
        text = re.sub(re.escape(key).replace("Q", r"\s*Q\s*"), value, text)
    return text


def cleanup_model_output(text: str) -> str:
    text = text.strip("\ufeff")
    text = re.sub(r"^\s*```(?:markdown|md)?\s*\n", "", text)
    text = re.sub(r"\n```\s*$", "", text)
    text = re.sub(r"(?ms)^\s*(?:Requirements|要求)：?\s*\n(?:-\s*.*\n)+\s*Markdown (?:fragment|片段)：?\s*\n", "", text)
    text = re.sub(r"(?m)^\s*(?:原文开始|翻译后的 Markdown 片段)：?\s*$\n?", "", text)
    return text


def cleanup_translated_document(text: str) -> str:
    """Remove only unambiguous prompt artifacts from an already translated file."""
    text = re.sub(r"(?m)^\s*```markdown\s*$\n?", "", text)
    prompt_block = (
        r"(?ms)^\s*(?:Requirements|要求)：?\s*\n"
        r"(?=[ \t]*-\s*(?:Translate the full text|忠实地翻译全文|"
        r"Preserve Markdown syntax|保留 Markdown 语法))"
        r".*?(?:^[ \t]*(?:Markdown fragment|Markdown 片段)：?\s*$\n)"
    )
    text = re.sub(prompt_block, "", text)
    text = re.sub(r"(?m)^[ \t]*Requirements:[ \t]*\n?", "", text)
    text = re.sub(r"(?<!\w)Requirements:[ \t]*", "", text)
    text = re.sub(
        r"(?m)^[ \t]*-\s*(?:Translate the full text faithfully|Do not summarize, omit, or add new content|"
        r"Preserve Markdown syntax.*|Preserve inline code.*|Preserve link targets.*|"
        r"Return only the translated Markdown fragment)\s*\n?",
        "",
        text,
    )
    text = re.sub(
        r"(?m)^[ \t]*-\s*(?:翻译全文，不要省略或增添内容|译文须忠实于原文.*|"
        r"保留 Markdown 语法.*|保留代码行.*|保留代码、命令.*|保留链接目标.*|"
        r"仅返回翻译后的 Markdown 片段。)\s*\n?",
        "",
        text,
    )
    text = re.sub(r"(?m)^[ \t]*原文(?:开始|结束)[ \t]*\n?", "", text)
    text = re.sub(r"(?m)^[ \t]*(?:Markdown fragment|Markdown 片段)：?[ \t]*\n?", "", text)
    text = re.sub(r"(?m)^[ \t]*-\s*仅返回翻译后的 Markdown 片段。\s*\n?", "", text)
    text = re.sub(r"(?m)^[ \t]*-\s*$\n?", "", text)
    text = re.sub(r"(?m)^[ \t]*:[ \t]*\n?", "", text)
    return text


def translate_chunk(chunk: str, engine: str, model: str) -> str:
    if engine == "ollama":
        return ollama_generate(model, PROMPT + chunk)
    if engine == "google":
        return google_translate(chunk)
    raise ValueError(f"unknown engine: {engine}")


def translate_markdown(text: str, engine: str, model: str, max_chars: int) -> str:
    output: list[str] = []
    for kind, part in split_fenced_blocks(text):
        if kind == "code" or not part.strip():
            output.append(part)
            continue
        for chunk in split_text_chunk(part, max_chars):
            if not chunk.strip():
                output.append(chunk)
                continue
            translated = translate_chunk(chunk, engine, model)
            if chunk.endswith("\n") and not translated.endswith("\n"):
                translated += "\n"
            output.append(translated)
    return "".join(output)


def zh_path_for(path: Path) -> Path:
    return path.with_name(f"{path.stem}_zh{path.suffix}")


def has_zh_target(base: Path, target: str) -> bool:
    if "://" in target or target.startswith(("#", "mailto:")):
        return False
    target_path = (base / target).resolve()
    zh_target = zh_path_for(target_path)
    return zh_target.exists()


def rewrite_target(target: str) -> str:
    p = Path(target)
    if p.stem.endswith("_zh"):
        return target
    return str(p.with_name(f"{p.stem}_zh{p.suffix}")).replace("\\", "/")


def rewrite_local_links(text: str, file_path: Path) -> str:
    base = file_path.parent

    def inline(match: re.Match[str]) -> str:
        target = match.group(1)
        fragment = match.group(2) or ""
        if has_zh_target(base, target):
            return f"]({rewrite_target(target)}{fragment})"
        return match.group(0)

    def reference(match: re.Match[str]) -> str:
        prefix, target, fragment, suffix = match.groups()
        if has_zh_target(base, target):
            return f"{prefix}{rewrite_target(target)}{fragment or ''}{suffix}"
        return match.group(0)

    text = INLINE_LINK_RE.sub(inline, text)
    return REF_LINK_RE.sub(reference, text)


def iter_source_docs(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*.md")
        if not path.stem.endswith("_zh")
    )


def should_translate(src: Path, dst: Path, force: bool) -> bool:
    if force or not dst.exists():
        return True
    src_size = src.stat().st_size
    dst_size = dst.stat().st_size
    return dst_size < max(1200, int(src_size * 0.45))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="docs", help="docs root")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Ollama model")
    parser.add_argument("--engine", choices=["google", "ollama"], default="google")
    parser.add_argument("--max-chars", type=int, default=4500)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--max-source-bytes", type=int, help="skip source files larger than this")
    parser.add_argument("--min-source-bytes", type=int, help="skip source files smaller than this")
    parser.add_argument("--no-rewrite-links", action="store_true")
    parser.add_argument("--cleanup-only", action="store_true")
    parser.add_argument("--only", nargs="*", help="specific source markdown files")
    args = parser.parse_args()

    root = Path(args.root)
    sources = [Path(p) for p in args.only] if args.only else iter_source_docs(root)
    if args.max_source_bytes is not None:
        sources = [p for p in sources if p.stat().st_size <= args.max_source_bytes]
    if args.min_source_bytes is not None:
        sources = [p for p in sources if p.stat().st_size >= args.min_source_bytes]

    if args.cleanup_only:
        for dst in root.rglob("*_zh.md"):
            text = dst.read_text(encoding="utf-8")
            fixed = cleanup_translated_document(text)
            if fixed != text:
                dst.write_text(fixed, encoding="utf-8", newline="\n")
                print(f"clean {dst}")
        return 0

    for src in sources:
        dst = zh_path_for(src)
        if not should_translate(src, dst, args.force):
            print(f"skip {dst}")
            continue
        print(f"translate {src} -> {dst}", flush=True)
        english = src.read_text(encoding="utf-8")
        chinese = translate_markdown(english, args.engine, args.model, args.max_chars)
        dst.write_text(chinese, encoding="utf-8", newline="\n")

    if not args.no_rewrite_links:
        for src in iter_source_docs(root):
            dst = zh_path_for(src)
            if not dst.exists():
                continue
            text = dst.read_text(encoding="utf-8")
            fixed = rewrite_local_links(text, dst)
            if fixed != text:
                dst.write_text(fixed, encoding="utf-8", newline="\n")
                print(f"rewrite links {dst}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
