#!/usr/bin/env python3
"""Embedded SQLite Episodic Memory & Dialogue Disentanglement Engine (`Turn -> Span -> Thread`).

Provides zero-daemon, stdlib-only (`sqlite3` + `struct` + `FTS5`) persistence for:
1. Compact IEEE-754 little-endian `float32` binary embedding BLOBs (`vector_cache` table),
   shared across all 5 federated graphs and atomic dialogue `Spans` (~70% smaller than JSON,
   concurrent-safe under SQLite `WAL` mode).
2. Three-layer Dialogue Disentanglement for multiplexed human-agent conversations:
   - `turns`   : Immutable physical turns (mirrored from portable `_aiHumanInteract/episodes/turns.jsonl`)
   - `spans`   : Sub-turn atomic topical Q&A slices with exact `(char_start, char_end)` offsets,
                 indexed by both dense embeddings and SQLite `FTS5` (`unicode61`) BM25 search
   - `threads` : Virtual single-topic timelines (`THR-###`) woven across interleaved turns,
                 supporting many-to-many cross-thread pollination (`thread_cross_refs`),
                 bidirectional graph-node bindings (`thread_node_links`), and per-thread
                 selective context folding (`folded` / `crystallized` 1-line capsules).
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
import struct
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

MEMORY_SCHEMA = "paths-to-modernity-memory-sqlite-v1"
PORTABLE_EPISODES_SCHEMA = "paths-to-modernity-episodes-v1"

TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_.-]{1,}|[\u4e00-\u9fff]{1,}")

CIRCLED_NUM_MAP = {
    "①": 1, "②": 2, "③": 3, "④": 4, "⑤": 5,
    "⑥": 6, "⑦": 7, "⑧": 8, "⑨": 9, "⑩": 10,
}
CN_NUM_MAP = {
    "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
}

# Top-level numbered item or markdown section heading
NUMBERED_ITEM_RE = re.compile(
    r"^(?P<indent>[ \t]{0,2})(?:(?P<num>\d{1,2})[.、)）]|[(（](?P<pnum>\d{1,2})[)）]|(?P<cnum>[①②③④⑤⑥⑦⑧⑨⑩]))[ \t]*",
    re.MULTILINE,
)
HEADING_ITEM_RE = re.compile(
    r"^(?P<hashes>#{1,4})[ \t]+(?:(?P<hnum>\d{1,2})[.、)）\s]+)?(?P<htitle>[^\n]+)",
    re.MULTILINE,
)
BACKREF_ITEM_RE = re.compile(
    r"(?:关于|针对|回到|接|结合|对应)?第\s*(?P<num>\d{1,2}|[一二三四五六七八九十])\s*(?:点|项|个问题|条|部分|问)"
)
EXPLICIT_THR_RE = re.compile(r"\b(THR-\d{3})\b", re.IGNORECASE)
EXPLICIT_NODE_RE = re.compile(r"\b((?:INT|SPEC|LT|MT|ST|WP|KD|EVAL)-\d{3})\b")
DISCOURSE_SHIFT_START_RE = re.compile(
    r"^\s*(?:另外|此外|顺便问|再问一[个点]|还有一[个点]|换个话题|附带问|其次|最后关于|关于第\s*(?:\d+|[一二三四五六七八九十])\s*[点项个条]|针对[^：:\n]{2,20}[：:])"
)
NEW_TOPIC_CUE_RE = re.compile(
    r"(?:另外(?:再|突然|顺便)?|顺便问|再问个新问题|换个话题|新问题|突然想到)"
)


def pack_f32(vec: Sequence[float]) -> bytes:
    """Pack float sequence into compact little-endian IEEE-754 float32 bytes."""
    n = len(vec)
    return struct.pack(f"<{n}f", *(float(x) for x in vec))


def unpack_f32(blob: bytes) -> list[float]:
    """Unpack little-endian IEEE-754 float32 bytes back into Python floats."""
    n = len(blob) // 4
    return [round(float(x), 6) for x in struct.unpack(f"<{n}f", blob[: n * 4])]


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or len(a) != len(b):
        return 0.0
    return sum(x * y for x, y in zip(a, b))


def _l2_norm(vec: Sequence[float]) -> list[float]:
    norm = math.sqrt(sum(float(x) * float(x) for x in vec))
    if norm <= 1e-12:
        return [0.0 for _ in vec]
    return [round(float(x) / norm, 6) for x in vec]


def _extract_lexical_tokens(text: str) -> set[str]:
    out: set[str] = set()
    for m in TOKEN_RE.finditer(text.lower()):
        tok = m.group(0)
        if "\u4e00" <= tok[0] <= "\u9fff":
            if len(tok) <= 4:
                out.add(tok)
            for i in range(len(tok) - 1):
                out.add(tok[i : i + 2])
        elif len(tok) >= 2 and tok not in {"the", "and", "for", "with", "that", "this", "from"}:
            out.add(tok)
    return out


def _parse_int_token(raw: str) -> int | None:
    raw = raw.strip()
    if raw.isdigit():
        return int(raw)
    if raw in CIRCLED_NUM_MAP:
        return CIRCLED_NUM_MAP[raw]
    if raw in CN_NUM_MAP:
        return CN_NUM_MAP[raw]
    return None


def _derive_topic_hint(text: str, max_len: int = 28) -> str:
    """Derive a clean, concise human-readable topic title from a slice of dialogue."""
    clean = re.sub(r"^\s*(?:[#*\->]+|\d+[.、)）]|[①②③④⑤⑥⑦⑧⑨⑩]|[(（]\d+[)）])\s*", "", text.strip())
    clean = re.sub(
        r"^(?:关于第\s*(?:\d+|[一二三四五六七八九十])\s*[点项个条问题]+[：:，,\s]*|另外[，,\s]*|顺便问一下[：:，,\s]*)",
        "",
        clean,
    )
    first_line = clean.splitlines()[0].strip() if clean.splitlines() else clean
    bold_m = re.match(r"^\*\*([^*]{3,32})\*\*", first_line)
    if bold_m:
        cand = bold_m.group(1).strip(" ：:·")
    else:
        clause = re.split(r"[。！？!?；;\n]", first_line)[0].strip(" ：:，,")
        cand = clause
    if len(cand) > max_len:
        cand = cand[:max_len].rstrip(" ，,、") + "…"
    return cand or "未命名对话议题"


def split_into_topical_blocks(text: str) -> list[dict[str, Any]]:
    """Split a single turn side (user or assistant) into topical blocks with exact char offsets."""
    if not text or not text.strip():
        return [{"item_num": None, "start": 0, "end": len(text), "text": text.strip()}]

    # 1. Check top-level numbered items (`1. ...`, `2. ...`, `① ...`) outside fenced code blocks
    fenced_ranges: list[tuple[int, int]] = []
    for fm in re.finditer(r"```.*?```", text, flags=re.DOTALL):
        fenced_ranges.append((fm.start(), fm.end()))

    def _in_fence(pos: int) -> bool:
        return any(s <= pos < e for s, e in fenced_ranges)

    num_matches = [m for m in NUMBERED_ITEM_RE.finditer(text) if not _in_fence(m.start())]
    if len(num_matches) >= 2:
        blocks: list[dict[str, Any]] = []
        prefix_end = num_matches[0].start()
        prefix_txt = text[:prefix_end].strip()
        for idx, m in enumerate(num_matches):
            seg_start = 0 if (idx == 0 and prefix_txt and len(prefix_txt) < 60) else m.start()
            seg_end = num_matches[idx + 1].start() if idx + 1 < len(num_matches) else len(text)
            raw_num = m.group("num") or m.group("pnum") or m.group("cnum") or ""
            inum = _parse_int_token(raw_num)
            seg_txt = text[seg_start:seg_end].strip()
            if idx == 0 and prefix_txt and len(prefix_txt) >= 60:
                blocks.append(
                    {
                        "item_num": None,
                        "start": 0,
                        "end": prefix_end,
                        "text": prefix_txt,
                    }
                )
                seg_start = m.start()
                seg_txt = text[seg_start:seg_end].strip()
            if seg_txt:
                blocks.append(
                    {
                        "item_num": inum,
                        "start": seg_start,
                        "end": seg_end,
                        "text": seg_txt,
                    }
                )
        if len(blocks) >= 2:
            return blocks

    # 2. Check Markdown headings (`## ...` / `### ...`)
    head_matches = [m for m in HEADING_ITEM_RE.finditer(text) if not _in_fence(m.start())]
    if len(head_matches) >= 2:
        levels = [len(m.group("hashes")) for m in head_matches]
        top_lvl = min(levels)
        top_heads = [m for m in head_matches if len(m.group("hashes")) == top_lvl]
        if len(top_heads) >= 2:
            blocks = []
            for idx, m in enumerate(top_heads):
                seg_start = 0 if idx == 0 else m.start()
                seg_end = top_heads[idx + 1].start() if idx + 1 < len(top_heads) else len(text)
                hnum = _parse_int_token(m.group("hnum") or "")
                seg_txt = text[seg_start:seg_end].strip()
                if seg_txt:
                    blocks.append(
                        {
                            "item_num": hnum,
                            "start": seg_start,
                            "end": seg_end,
                            "text": seg_txt,
                        }
                    )
            if len(blocks) >= 2:
                return blocks

    # 3. Check blank-line paragraphs with explicit discourse topic-shift cues (`关于第2点...`, `另外...`)
    para_spans: list[tuple[int, int, str]] = []
    cursor = 0
    for pm in re.finditer(r"\n\s*\n+", text):
        if _in_fence(pm.start()):
            continue
        chunk = text[cursor : pm.start()]
        if chunk.strip():
            para_spans.append((cursor, pm.start(), chunk.strip()))
        cursor = pm.end()
    if cursor < len(text) and text[cursor:].strip():
        para_spans.append((cursor, len(text), text[cursor:].strip()))

    if len(para_spans) >= 2:
        shift_count = sum(
            1 for idx, (_, _, ptxt) in enumerate(para_spans)
            if idx > 0 and DISCOURSE_SHIFT_START_RE.search(ptxt)
        )
        all_have_backref = sum(1 for _, _, ptxt in para_spans if BACKREF_ITEM_RE.search(ptxt)) >= 2
        if shift_count >= 1 or all_have_backref:
            merged_paras: list[dict[str, Any]] = []
            for idx, (ps, pe, ptxt) in enumerate(para_spans):
                bref = BACKREF_ITEM_RE.search(ptxt[:40])
                inum = _parse_int_token(bref.group("num")) if bref else None
                if idx == 0 or DISCOURSE_SHIFT_START_RE.search(ptxt) or inum is not None:
                    merged_paras.append(
                        {"item_num": inum, "start": ps, "end": pe, "text": ptxt}
                    )
                else:
                    # Continuation paragraph of the current topic
                    prev = merged_paras[-1]
                    prev["end"] = pe
                    prev["text"] = text[prev["start"] : pe].strip()
            if len(merged_paras) >= 2:
                return merged_paras

    return [{"item_num": None, "start": 0, "end": len(text), "text": text.strip()}]


def demux_turn_to_spans(user_text: str, assistant_text: str) -> list[dict[str, Any]]:
    """Disentangle a physical `(user_text, assistant_text)` turn into 1..K atomic topical Spans."""
    u_blocks = split_into_topical_blocks(user_text)

    # Crucial human-centric rule: if the user asked ONE cohesive question, keep the turn as 1 Span
    # even if the assistant formatted its answer as a 3-point list!
    if len(u_blocks) <= 1:
        ub = u_blocks[0]
        brefs = [
            _parse_int_token(m.group("num"))
            for m in BACKREF_ITEM_RE.finditer(ub["text"])
        ]
        return [
            {
                "span_index": 1,
                "topic_hint": _derive_topic_hint(ub["text"]),
                "user_slice": ub["text"],
                "assistant_slice": assistant_text.strip(),
                "user_char_start": ub["start"],
                "user_char_end": ub["end"],
                "asst_char_start": 0,
                "asst_char_end": len(assistant_text),
                "backref_nums": [x for x in brefs if x is not None],
                "explicit_threads": [m.upper() for m in EXPLICIT_THR_RE.findall(ub["text"] + " " + assistant_text)],
                "explicit_nodes": sorted(set(EXPLICIT_NODE_RE.findall(ub["text"] + " " + assistant_text))),
                "has_new_topic_cue": bool(NEW_TOPIC_CUE_RE.search(ub["text"][:50])),
            }
        ]

    a_blocks = split_into_topical_blocks(assistant_text)
    assigned_asst: dict[int, list[dict[str, Any]]] = defaultdict(list)

    if len(a_blocks) == 1:
        # Assistant gave one integrated reply; attach full slice so each span remains self-contained
        for i in range(len(u_blocks)):
            assigned_asst[i].append(a_blocks[0])
    elif len(a_blocks) == len(u_blocks):
        # 1-to-1 structural correspondence (or explicit matching item numbers)
        u_num_to_idx = {
            ub["item_num"]: i for i, ub in enumerate(u_blocks) if ub["item_num"] is not None
        }
        used_a: set[int] = set()
        for a_i, ab in enumerate(a_blocks):
            if ab["item_num"] is not None and ab["item_num"] in u_num_to_idx:
                assigned_asst[u_num_to_idx[ab["item_num"]]].append(ab)
                used_a.add(a_i)
        if len(used_a) < len(a_blocks):
            assigned_asst.clear()
            for i, ab in enumerate(a_blocks):
                assigned_asst[i].append(ab)
    else:
        # Asymmetric multi-block reply: match each assistant block to its closest user block
        u_tokens = [_extract_lexical_tokens(ub["text"]) for ub in u_blocks]
        u_num_to_idx = {
            ub["item_num"]: i for i, ub in enumerate(u_blocks) if ub["item_num"] is not None
        }
        for a_i, ab in enumerate(a_blocks):
            if ab["item_num"] is not None and ab["item_num"] in u_num_to_idx:
                assigned_asst[u_num_to_idx[ab["item_num"]]].append(ab)
                continue
            atok = _extract_lexical_tokens(ab["text"])
            best_u = min(len(u_blocks) - 1, round(a_i * (len(u_blocks) - 1) / max(1, len(a_blocks) - 1)))
            best_ov = -1.0
            for u_i, utok in enumerate(u_tokens):
                ov = len(utok & atok) / max(1, len(utok)) if utok else 0.0
                if ov > best_ov + 0.02:
                    best_ov = ov
                    best_u = u_i
            assigned_asst[best_u].append(ab)

    spans: list[dict[str, Any]] = []
    for i, ub in enumerate(u_blocks):
        matched_a = assigned_asst.get(i) or [a_blocks[min(i, len(a_blocks) - 1)]]
        a_start = min(x["start"] for x in matched_a)
        a_end = max(x["end"] for x in matched_a)
        a_slice = "\n\n".join(x["text"] for x in matched_a).strip()
        brefs = [
            _parse_int_token(m.group("num"))
            for m in BACKREF_ITEM_RE.finditer(ub["text"])
        ]
        combined_txt = ub["text"] + "\n" + a_slice
        spans.append(
            {
                "span_index": i + 1,
                "item_num": ub["item_num"],
                "topic_hint": _derive_topic_hint(ub["text"]),
                "user_slice": ub["text"],
                "assistant_slice": a_slice,
                "user_char_start": ub["start"],
                "user_char_end": ub["end"],
                "asst_char_start": a_start,
                "asst_char_end": a_end,
                "backref_nums": [x for x in brefs if x is not None],
                "explicit_threads": [m.upper() for m in EXPLICIT_THR_RE.findall(combined_txt)],
                "explicit_nodes": sorted(set(EXPLICIT_NODE_RE.findall(combined_txt))),
                "has_new_topic_cue": bool(NEW_TOPIC_CUE_RE.search(ub["text"][:50])),
            }
        )
    return spans


class SqliteVectorStore:
    """Concurrent WAL-mode SQLite binary float32 vector cache."""

    def __init__(self, db_path: Path, legacy_json_path: Path | None = None) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        if legacy_json_path and legacy_json_path.is_file():
            self._migrate_legacy_json_once(legacy_json_path)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=15.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS vector_cache (
                    cache_key TEXT PRIMARY KEY,
                    model_id TEXT NOT NULL,
                    dim INTEGER NOT NULL,
                    vec_blob BLOB NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            conn.execute(
                "INSERT OR REPLACE INTO meta(key, value) VALUES ('schema_version', ?)",
                (MEMORY_SCHEMA,),
            )

    def _migrate_legacy_json_once(self, json_path: Path) -> None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM meta WHERE key = 'migrated_legacy_json'"
            ).fetchone()
            if row:
                return
            try:
                raw = json.loads(json_path.read_text(encoding="utf-8"))
                vectors = raw.get("vectors", {}) if isinstance(raw, dict) else {}
                model_id = str(raw.get("model_id", "legacy")) if isinstance(raw, dict) else "legacy"
            except (OSError, json.JSONDecodeError):
                vectors = {}
                model_id = "legacy"
            now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            if vectors:
                rows = [
                    (ckey, ckey.split(":", 1)[0] if ":" in ckey else model_id, len(vec), pack_f32(vec), now)
                    for ckey, vec in vectors.items()
                    if isinstance(vec, list) and vec
                ]
                conn.executemany(
                    "INSERT OR IGNORE INTO vector_cache(cache_key, model_id, dim, vec_blob, updated_at) VALUES (?, ?, ?, ?, ?)",
                    rows,
                )
            conn.execute(
                "INSERT OR REPLACE INTO meta(key, value) VALUES ('migrated_legacy_json', ?)",
                (now,),
            )

    def get_many(self, keys: Sequence[str]) -> dict[str, list[float]]:
        if not keys:
            return {}
        unique_keys = list(dict.fromkeys(keys))
        out: dict[str, list[float]] = {}
        with self._connect() as conn:
            chunk_size = 400
            for i in range(0, len(unique_keys), chunk_size):
                sub = unique_keys[i : i + chunk_size]
                placeholders = ",".join("?" for _ in sub)
                rows = conn.execute(
                    f"SELECT cache_key, vec_blob FROM vector_cache WHERE cache_key IN ({placeholders})",
                    sub,
                ).fetchall()
                for ckey, blob in rows:
                    out[ckey] = unpack_f32(blob)
        return out

    def put_many(self, model_id: str, items: Mapping[str, Sequence[float]]) -> None:
        if not items:
            return
        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        rows = [
            (ckey, model_id, len(vec), pack_f32(vec), now)
            for ckey, vec in items.items()
            if vec
        ]
        if not rows:
            return
        with self._connect() as conn:
            conn.executemany(
                "INSERT OR REPLACE INTO vector_cache(cache_key, model_id, dim, vec_blob, updated_at) VALUES (?, ?, ?, ?, ?)",
                rows,
            )

    def count(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) FROM vector_cache").fetchone()
            return int(row[0]) if row else 0


class EpisodicMemoryStore:
    """Manages SQLite `turns`, `spans` (+ `FTS5`), `threads` (`THR-###`), folding capsules & graph bindings."""

    def __init__(
        self,
        repo_root: Path,
        *,
        embed_fn: Callable[[Sequence[str], bool, bool], list[list[float]]] | None = None,
        backend_name: str = "hash",
        effective_model_id: str = "ptm-stdlib-ngram-384",
    ) -> None:
        self.repo_root = repo_root.resolve()
        self.db_path = self.repo_root / "_aiHumanInteract" / ".cache" / "memory.sqlite"
        self.episodes_dir = self.repo_root / "_aiHumanInteract" / "episodes"
        self.turns_jsonl_path = self.episodes_dir / "turns.jsonl"
        self.thread_state_path = self.episodes_dir / "thread_state.json"
        self.embed_fn = embed_fn
        self.backend_name = backend_name
        self.effective_model_id = effective_model_id
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.has_fts5 = False
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=15.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS vector_cache (
                    cache_key TEXT PRIMARY KEY,
                    model_id TEXT NOT NULL,
                    dim INTEGER NOT NULL,
                    vec_blob BLOB NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS turns (
                    turn_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    turn_index INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    user_text TEXT NOT NULL,
                    assistant_text TEXT NOT NULL,
                    span_count INTEGER NOT NULL DEFAULT 1,
                    content_sha256 TEXT NOT NULL UNIQUE
                );
                CREATE TABLE IF NOT EXISTS spans (
                    span_id TEXT PRIMARY KEY,
                    turn_id TEXT NOT NULL REFERENCES turns(turn_id) ON DELETE CASCADE,
                    span_index INTEGER NOT NULL,
                    span_total INTEGER NOT NULL DEFAULT 1,
                    topic_hint TEXT NOT NULL,
                    user_slice TEXT NOT NULL,
                    assistant_slice TEXT NOT NULL,
                    user_char_start INTEGER NOT NULL,
                    user_char_end INTEGER NOT NULL,
                    asst_char_start INTEGER NOT NULL,
                    asst_char_end INTEGER NOT NULL,
                    vec_blob BLOB
                );
                CREATE TABLE IF NOT EXISTS threads (
                    thread_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    capsule_summary TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    centroid_blob BLOB
                );
                CREATE TABLE IF NOT EXISTS thread_spans (
                    thread_id TEXT NOT NULL REFERENCES threads(thread_id) ON DELETE CASCADE,
                    span_id TEXT NOT NULL REFERENCES spans(span_id) ON DELETE CASCADE,
                    position INTEGER NOT NULL,
                    role TEXT NOT NULL DEFAULT 'primary',
                    confidence REAL NOT NULL DEFAULT 1.0,
                    PRIMARY KEY (thread_id, span_id)
                );
                CREATE TABLE IF NOT EXISTS thread_cross_refs (
                    from_thread TEXT NOT NULL REFERENCES threads(thread_id) ON DELETE CASCADE,
                    to_thread TEXT NOT NULL REFERENCES threads(thread_id) ON DELETE CASCADE,
                    via_span_id TEXT NOT NULL REFERENCES spans(span_id) ON DELETE CASCADE,
                    PRIMARY KEY (from_thread, to_thread, via_span_id)
                );
                CREATE TABLE IF NOT EXISTS thread_node_links (
                    thread_id TEXT NOT NULL REFERENCES threads(thread_id) ON DELETE CASCADE,
                    node_id TEXT NOT NULL,
                    provenance TEXT NOT NULL DEFAULT 'declared',
                    confidence REAL NOT NULL DEFAULT 1.0,
                    PRIMARY KEY (thread_id, node_id)
                );
                """
            )
            try:
                conn.execute(
                    """
                    CREATE VIRTUAL TABLE IF NOT EXISTS spans_fts USING fts5(
                        span_id UNINDEXED,
                        topic_hint,
                        user_slice,
                        assistant_slice,
                        tokenize='unicode61'
                    );
                    """
                )
                self.has_fts5 = True
            except sqlite3.OperationalError:
                self.has_fts5 = False

    def _embed(self, texts: Sequence[str], is_query: bool = False, persist: bool = True) -> list[list[float]]:
        if not texts:
            return []
        if self.embed_fn is not None:
            return self.embed_fn(texts, is_query, persist)
        from ptm_hebbian import _stdlib_hash_embed
        return [_stdlib_hash_embed(t) for t in texts]

    def _load_thread_state_overrides(self) -> dict[str, dict[str, Any]]:
        if not self.thread_state_path.is_file():
            return {}
        try:
            raw = json.loads(self.thread_state_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                return raw.get("threads", {})
        except (OSError, json.JSONDecodeError):
            pass
        return {}

    def _save_thread_state_overrides(self, overrides: Mapping[str, Any]) -> None:
        self.episodes_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": PORTABLE_EPISODES_SCHEMA,
            "threads": dict(sorted(overrides.items())),
        }
        self.thread_state_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    def _next_turn_id(self, conn: sqlite3.Connection) -> tuple[str, int]:
        rows = conn.execute("SELECT turn_id, turn_index FROM turns").fetchall()
        nums = []
        max_idx = 0
        for r in rows:
            max_idx = max(max_idx, int(r["turn_index"]))
            try:
                nums.append(int(str(r["turn_id"]).split("-")[1]))
            except (IndexError, ValueError):
                pass
        nxt = (max(nums) + 1) if nums else 1
        return f"TURN-{nxt:04d}", max_idx + 1

    def _next_thread_id(self, conn: sqlite3.Connection) -> str:
        rows = conn.execute("SELECT thread_id FROM threads").fetchall()
        nums = []
        for r in rows:
            try:
                nums.append(int(str(r["thread_id"]).split("-")[1]))
            except (IndexError, ValueError):
                pass
        nxt = (max(nums) + 1) if nums else 1
        return f"THR-{nxt:03d}"

    def ingest_turn(
        self,
        *,
        user_text: str,
        assistant_text: str,
        session_id: str = "SES-01",
        timestamp: str | None = None,
        turn_id: str | None = None,
        turn_index: int | None = None,
        hint_nodes: Sequence[str] = (),
        append_portable_jsonl: bool = True,
    ) -> dict[str, Any]:
        """Ingest one physical turn, disentangle sub-turn Spans, and weave into Virtual Threads."""
        u_clean = user_text.strip()
        a_clean = assistant_text.strip()
        if not u_clean and not a_clean:
            raise ValueError("Cannot ingest an empty turn.")

        ts = timestamp or datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        digest = hashlib.sha256(f"{session_id}\n{u_clean}\n---\n{a_clean}".encode("utf-8")).hexdigest()

        if self.embed_fn is not None:
            self._reembed_spans_if_needed()

        with self._connect() as conn:
            existing = conn.execute(
                "SELECT turn_id FROM turns WHERE content_sha256 = ?", (digest,)
            ).fetchone()
            if existing:
                tid_existing = str(existing["turn_id"])
                sp_rows = conn.execute(
                    "SELECT span_id FROM spans WHERE turn_id = ? ORDER BY span_index",
                    (tid_existing,),
                ).fetchall()
                th_rows = conn.execute(
                    """
                    SELECT DISTINCT ts.thread_id
                    FROM thread_spans ts
                    JOIN spans s ON s.span_id = ts.span_id
                    WHERE s.turn_id = ?
                    ORDER BY ts.thread_id
                    """,
                    (tid_existing,),
                ).fetchall()
                return {
                    "turn_id": tid_existing,
                    "deduplicated": True,
                    "span_ids": [str(r["span_id"]) for r in sp_rows],
                    "thread_ids": [str(r["thread_id"]) for r in th_rows],
                }

            alloc_tid, alloc_idx = self._next_turn_id(conn)
            final_tid = turn_id or alloc_tid
            final_idx = turn_index if turn_index is not None else alloc_idx

            # Reconstruct session logical topic slots (`1 -> THR-001, 2 -> THR-002, 3 -> THR-003`)
            # so if Turn 2 skips #2 (`关于第1点... 关于第3点...`), Turn 3's `关于第2点` still resolves to THR-002!
            session_slot_map: dict[int, str] = {}
            prior_srows = conn.execute(
                """
                SELECT s.span_index, s.user_slice, ts.thread_id
                FROM spans s
                JOIN turns t ON t.turn_id = s.turn_id
                JOIN thread_spans ts ON ts.span_id = s.span_id AND ts.role = 'primary'
                WHERE t.session_id = ?
                ORDER BY t.turn_index ASC, s.span_index ASC
                """,
                (session_id,),
            ).fetchall()
            for psr in prior_srows:
                u_txt = str(psr["user_slice"])
                b_m = BACKREF_ITEM_RE.search(u_txt[:36])
                n_m = NUMBERED_ITEM_RE.match(u_txt)
                slot: int | None = None
                if b_m:
                    slot = _parse_int_token(b_m.group("num"))
                elif n_m:
                    slot = _parse_int_token(
                        n_m.group("num") or n_m.group("pnum") or n_m.group("cnum") or ""
                    )
                if slot is not None and slot not in session_slot_map:
                    session_slot_map[slot] = str(psr["thread_id"])
                elif int(psr["span_index"]) not in session_slot_map:
                    session_slot_map[int(psr["span_index"])] = str(psr["thread_id"])

            raw_spans = demux_turn_to_spans(u_clean, a_clean)
            span_texts = [
                f"[Dialogue Span: {sp['topic_hint']}] User: {sp['user_slice']}\nAssistant: {sp['assistant_slice']}"
                for sp in raw_spans
            ]
            span_vecs = self._embed(span_texts, False, True)

            conn.execute(
                """
                INSERT INTO turns(turn_id, session_id, turn_index, timestamp, user_text, assistant_text, span_count, content_sha256)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (final_tid, session_id, final_idx, ts, u_clean, a_clean, len(raw_spans), digest),
            )

            # Load current threads & their centroids + lexical sets for weaving (isolating vector space per model_id)
            centroid_meta_row = conn.execute(
                "SELECT value FROM meta WHERE key = 'centroid_model_id'"
            ).fetchone()
            stored_centroid_model = str(centroid_meta_row["value"]) if centroid_meta_row else None
            existing_threads: dict[str, dict[str, Any]] = {}
            for trow in conn.execute("SELECT * FROM threads").fetchall():
                th_id = str(trow["thread_id"])
                c_blob = trow["centroid_blob"]
                s_rows = conn.execute(
                    """
                    SELECT s.topic_hint, s.user_slice, s.assistant_slice
                    FROM spans s
                    JOIN thread_spans ts ON ts.span_id = s.span_id
                    WHERE ts.thread_id = ?
                    """,
                    (th_id,),
                ).fetchall()
                if c_blob and (stored_centroid_model == self.effective_model_id or self.embed_fn is None):
                    c_vec = unpack_f32(c_blob)
                elif s_rows:
                    th_span_texts = [
                        f"[Dialogue Span: {sr['topic_hint']}] User: {sr['user_slice']}\nAssistant: {sr['assistant_slice']}"
                        for sr in s_rows
                    ]
                    th_vecs = self._embed(th_span_texts, False, True)
                    dim_th = len(th_vecs[0]) if th_vecs else 0
                    c_vec = (
                        _l2_norm([sum(v[k] for v in th_vecs) / len(th_vecs) for k in range(dim_th)])
                        if dim_th
                        else []
                    )
                    if c_vec:
                        conn.execute(
                            "UPDATE threads SET centroid_blob = ? WHERE thread_id = ?",
                            (pack_f32(c_vec), th_id),
                        )
                else:
                    c_vec = []
                kw_union = _extract_lexical_tokens(str(trow["title"]))
                for sr in s_rows:
                    kw_union |= _extract_lexical_tokens(
                        f"{sr['topic_hint']} {sr['user_slice']} {sr['assistant_slice']}"
                    )
                existing_threads[th_id] = {
                    "title": str(trow["title"]),
                    "vec": c_vec,
                    "kws": kw_union,
                    "span_count": len(s_rows),
                }
            conn.execute(
                "INSERT OR REPLACE INTO meta(key, value) VALUES ('centroid_model_id', ?)",
                (self.effective_model_id,),
            )
            conn.execute(
                "INSERT OR REPLACE INTO meta(key, value) VALUES ('spans_model_id', ?)",
                (self.effective_model_id,),
            )

            is_dense = self.backend_name in {"mlx", "openai"}
            merge_thresh = 0.56 if is_dense else 0.25
            created_span_ids: list[str] = []
            touched_threads: list[str] = []
            current_turn_span_threads: dict[int, str] = {}

            for sp, svec in zip(raw_spans, span_vecs):
                sidx = int(sp["span_index"])
                span_id = f"SPAN-{final_tid.split('-')[1]}.{sidx}"
                created_span_ids.append(span_id)
                conn.execute(
                    """
                    INSERT INTO spans(
                        span_id, turn_id, span_index, span_total, topic_hint,
                        user_slice, assistant_slice,
                        user_char_start, user_char_end, asst_char_start, asst_char_end, vec_blob
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        span_id,
                        final_tid,
                        sidx,
                        len(raw_spans),
                        sp["topic_hint"],
                        sp["user_slice"],
                        sp["assistant_slice"],
                        sp["user_char_start"],
                        sp["user_char_end"],
                        sp["asst_char_start"],
                        sp["asst_char_end"],
                        pack_f32(svec),
                    ),
                )
                if self.has_fts5:
                    conn.execute("DELETE FROM spans_fts WHERE span_id = ?", (span_id,))
                    conn.execute(
                        "INSERT INTO spans_fts(span_id, topic_hint, user_slice, assistant_slice) VALUES (?, ?, ?, ?)",
                        (span_id, sp["topic_hint"], sp["user_slice"], sp["assistant_slice"]),
                    )

                sp_kws = _extract_lexical_tokens(
                    f"{sp['topic_hint']} {sp['user_slice']} {sp['assistant_slice']}"
                )
                explicit_thrs = [t for t in sp["explicit_threads"] if t in existing_threads]
                backref_thrs: list[str] = []
                for bnum in sp["backref_nums"]:
                    if bnum in current_turn_span_threads and bnum < sidx:
                        backref_thrs.append(current_turn_span_threads[bnum])
                    elif bnum in session_slot_map:
                        backref_thrs.append(session_slot_map[bnum])

                scored_threads: list[tuple[float, str]] = []
                for th_id, tinfo in existing_threads.items():
                    raw_sim = _cosine(svec, tinfo["vec"]) if tinfo["vec"] else 0.0
                    norm_sim = (
                        max(0.0, (raw_sim + 1.0) / 2.0)
                        if is_dense
                        else max(0.0, raw_sim)
                    )
                    kw_ov = (
                        len(sp_kws & tinfo["kws"]) / max(1, min(len(sp_kws), 18))
                        if sp_kws and tinfo["kws"]
                        else 0.0
                    )
                    score = 0.72 * norm_sim + 0.34 * kw_ov
                    if th_id in explicit_thrs:
                        score += 0.48
                    if th_id in backref_thrs:
                        score += 0.40
                    if sp["has_new_topic_cue"] and th_id not in explicit_thrs and th_id not in backref_thrs:
                        score -= 0.14
                    scored_threads.append((score, th_id))

                scored_threads.sort(reverse=True)
                chosen_primary: str | None = None
                primary_conf = 1.0
                if scored_threads and scored_threads[0][0] >= merge_thresh:
                    chosen_primary = scored_threads[0][1]
                    primary_conf = round(min(1.0, scored_threads[0][0]), 4)

                if chosen_primary is None:
                    chosen_primary = self._next_thread_id(conn)
                    conn.execute(
                        """
                        INSERT INTO threads(thread_id, title, status, capsule_summary, created_at, updated_at, centroid_blob)
                        VALUES (?, ?, 'active', NULL, ?, ?, ?)
                        """,
                        (chosen_primary, sp["topic_hint"], ts, ts, pack_f32(svec)),
                    )
                    existing_threads[chosen_primary] = {
                        "title": sp["topic_hint"],
                        "vec": list(svec),
                        "kws": set(sp_kws),
                        "span_count": 1,
                    }
                    pos = 1
                else:
                    tinfo = existing_threads[chosen_primary]
                    cnt = tinfo["span_count"]
                    old_v = tinfo["vec"]
                    new_centroid = (
                        _l2_norm([(old_v[k] * cnt + svec[k]) / (cnt + 1) for k in range(len(svec))])
                        if len(old_v) == len(svec)
                        else list(svec)
                    )
                    tinfo["vec"] = new_centroid
                    tinfo["kws"] |= sp_kws
                    tinfo["span_count"] = cnt + 1
                    pos = cnt + 1
                    conn.execute(
                        "UPDATE threads SET updated_at = ?, centroid_blob = ? WHERE thread_id = ?",
                        (ts, pack_f32(new_centroid), chosen_primary),
                    )

                current_turn_span_threads[sidx] = chosen_primary
                if chosen_primary not in touched_threads:
                    touched_threads.append(chosen_primary)

                conn.execute(
                    """
                    INSERT OR REPLACE INTO thread_spans(thread_id, span_id, position, role, confidence)
                    VALUES (?, ?, ?, 'primary', ?)
                    """,
                    (chosen_primary, span_id, pos, primary_conf),
                )

                # Secondary cross-thread pollination (recorded cleanly in `thread_cross_refs` without polluting peer primary timelines)
                secondary_candidates = set(explicit_thrs) | set(backref_thrs)
                for sc_score, sc_tid in scored_threads[1:3]:
                    if sc_score >= merge_thresh + 0.16:
                        secondary_candidates.add(sc_tid)
                secondary_candidates.discard(chosen_primary)
                for sec_tid in sorted(secondary_candidates):
                    if sec_tid not in existing_threads:
                        continue
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO thread_cross_refs(from_thread, to_thread, via_span_id)
                        VALUES (?, ?, ?)
                        """,
                        (chosen_primary, sec_tid, span_id),
                    )

                # Explicit graph node IDs mentioned directly inside this span
                node_targets = set(sp["explicit_nodes"])
                if len(raw_spans) == 1:
                    node_targets.update(hint_nodes)
                for nid in sorted(node_targets):
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO thread_node_links(thread_id, node_id, provenance, confidence)
                        VALUES (?, ?, 'declared', 1.0)
                        """,
                        (chosen_primary, nid),
                    )

        if append_portable_jsonl:
            self.episodes_dir.mkdir(parents=True, exist_ok=True)
            rec = {
                "turn_id": final_tid,
                "session_id": session_id,
                "turn_index": final_idx,
                "timestamp": ts,
                "user_text": u_clean,
                "assistant_text": a_clean,
            }
            if hint_nodes:
                rec["hint_nodes"] = list(hint_nodes)
            with self.turns_jsonl_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

        self.apply_portable_thread_state()
        return {
            "turn_id": final_tid,
            "deduplicated": False,
            "span_count": len(created_span_ids),
            "span_ids": created_span_ids,
            "thread_ids": touched_threads,
        }

    def import_jsonl_transcript(self, jsonl_path: Path, session_id: str = "SES-IMPORT") -> dict[str, Any]:
        """Import either PtM `{user_text, assistant_text}` JSONL or chat `{role, content}` JSONL."""
        raw_lines = [
            ln.strip()
            for ln in jsonl_path.read_text(encoding="utf-8", errors="replace").splitlines()
            if ln.strip()
        ]
        records = [json.loads(ln) for ln in raw_lines]
        ingested = 0
        deduped = 0
        pending_user: str | None = None
        pending_ts: str | None = None

        for rec in records:
            if not isinstance(rec, dict):
                continue
            if "user_text" in rec and "assistant_text" in rec:
                res = self.ingest_turn(
                    user_text=str(rec["user_text"]),
                    assistant_text=str(rec["assistant_text"]),
                    session_id=str(rec.get("session_id") or session_id),
                    timestamp=rec.get("timestamp"),
                    turn_id=rec.get("turn_id"),
                    turn_index=rec.get("turn_index"),
                    hint_nodes=rec.get("hint_nodes") or (),
                    append_portable_jsonl=(jsonl_path.resolve() != self.turns_jsonl_path.resolve()),
                )
                if res["deduplicated"]:
                    deduped += 1
                else:
                    ingested += 1
                continue

            role = str(rec.get("role", "")).lower()
            content = rec.get("content", "")
            if isinstance(content, list):
                content = "\n".join(
                    str(part.get("text", "")) for part in content if isinstance(part, dict)
                )
            content_str = str(content).strip()
            if role in {"user", "human"} and content_str:
                pending_user = f"{pending_user}\n\n{content_str}" if pending_user else content_str
                pending_ts = pending_ts or rec.get("timestamp")
            elif role in {"assistant", "model", "agent"} and content_str and pending_user:
                res = self.ingest_turn(
                    user_text=pending_user,
                    assistant_text=content_str,
                    session_id=str(rec.get("session_id") or session_id),
                    timestamp=pending_ts or rec.get("timestamp"),
                    append_portable_jsonl=True,
                )
                pending_user = None
                pending_ts = None
                if res["deduplicated"]:
                    deduped += 1
                else:
                    ingested += 1

        return {"ingested_turns": ingested, "deduplicated_turns": deduped}

    def _reembed_spans_if_needed(self) -> None:
        """Keep `spans.vec_blob` and `threads.centroid_blob` homogeneous in `self.effective_model_id` without probe calls."""
        if self.embed_fn is None:
            return
        with self._connect() as conn:
            srows = conn.execute(
                "SELECT span_id, topic_hint, user_slice, assistant_slice, vec_blob FROM spans ORDER BY span_id"
            ).fetchall()
            if not srows:
                return
            meta_row = conn.execute(
                "SELECT value FROM meta WHERE key = 'spans_model_id'"
            ).fetchone()
            stored_model = str(meta_row["value"]) if meta_row else None
            model_changed = stored_model != self.effective_model_id
            needs = (
                list(srows)
                if model_changed
                else [r for r in srows if not r["vec_blob"]]
            )
            if not needs:
                return
            texts = [
                f"[Dialogue Span: {r['topic_hint']}] User: {r['user_slice']}\nAssistant: {r['assistant_slice']}"
                for r in needs
            ]
            new_vecs = self._embed(texts, False, True)
            for r, vec in zip(needs, new_vecs):
                conn.execute(
                    "UPDATE spans SET vec_blob = ? WHERE span_id = ?",
                    (pack_f32(vec), str(r["span_id"])),
                )
            for trow in conn.execute("SELECT thread_id FROM threads").fetchall():
                tid = str(trow["thread_id"])
                blobs = [
                    unpack_f32(sr["vec_blob"])
                    for sr in conn.execute(
                        """
                        SELECT s.vec_blob
                        FROM spans s
                        JOIN thread_spans ts ON ts.span_id = s.span_id AND ts.role = 'primary'
                        WHERE ts.thread_id = ?
                        """,
                        (tid,),
                    ).fetchall()
                    if sr["vec_blob"]
                ]
                if blobs:
                    dim = len(blobs[0])
                    avg = _l2_norm(
                        [sum(b[d] for b in blobs) / len(blobs) for d in range(dim)]
                    )
                    conn.execute(
                        "UPDATE threads SET centroid_blob = ? WHERE thread_id = ?",
                        (pack_f32(avg), tid),
                    )
            conn.execute(
                "INSERT OR REPLACE INTO meta(key, value) VALUES ('spans_model_id', ?)",
                (self.effective_model_id,),
            )
            conn.execute(
                "INSERT OR REPLACE INTO meta(key, value) VALUES ('centroid_model_id', ?)",
                (self.effective_model_id,),
            )

    def sync_portable_episodes(self, federated: Mapping[str, Any] | None = None) -> dict[str, Any]:
        """Ensure `_aiHumanInteract/episodes/turns.jsonl` & `thread_state.json` are synced into SQLite."""
        if self.turns_jsonl_path.is_file():
            self.import_jsonl_transcript(self.turns_jsonl_path)
        self._reembed_spans_if_needed()
        self.apply_portable_thread_state()
        if federated is not None:
            self.bind_threads_to_federated_graphs(federated)
        return self.export_summary()

    def apply_portable_thread_state(self) -> None:
        overrides = self._load_thread_state_overrides()
        if not overrides:
            return
        with self._connect() as conn:
            for tid, cfg in overrides.items():
                row = conn.execute(
                    "SELECT thread_id FROM threads WHERE thread_id = ?", (tid,)
                ).fetchone()
                if not row or not isinstance(cfg, dict):
                    continue
                if cfg.get("title"):
                    conn.execute(
                        "UPDATE threads SET title = ? WHERE thread_id = ?",
                        (str(cfg["title"]).strip(), tid),
                    )
                if cfg.get("status"):
                    conn.execute(
                        "UPDATE threads SET status = ? WHERE thread_id = ?",
                        (str(cfg["status"]).strip(), tid),
                    )
                if "capsule_summary" in cfg and cfg["capsule_summary"]:
                    conn.execute(
                        "UPDATE threads SET capsule_summary = ? WHERE thread_id = ?",
                        (str(cfg["capsule_summary"]).strip(), tid),
                    )
                for nid in cfg.get("node_refs") or []:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO thread_node_links(thread_id, node_id, provenance, confidence)
                        VALUES (?, ?, 'declared', 1.0)
                        """,
                        (tid, str(nid).strip()),
                    )

    def fold_thread(
        self,
        thread_id: str,
        *,
        capsule_summary: str | None = None,
        status: str = "folded",
        node_refs: Sequence[str] = (),
        title: str | None = None,
    ) -> dict[str, Any]:
        """Fold a completed thread into a compact 1-line capsule while keeping all Spans in SQLite."""
        if status not in {"active", "resolved", "folded", "crystallized"}:
            raise ValueError(f"Invalid thread status: {status}")
        detail = self.get_thread(thread_id)
        if detail is None:
            raise ValueError(f"Unknown thread ID: {thread_id}")

        clean_nodes = [n.strip() for n in node_refs if n.strip()]
        existing_nodes = [lnk["node_id"] for lnk in detail["linked_nodes"]]
        merged_nodes = sorted(set(existing_nodes) | set(clean_nodes))

        if not capsule_summary:
            # Deterministic crisp capsule from first user question + final assistant conclusion + linked nodes
            spans = detail["spans"]
            last_a = re.split(r"[。\n]", spans[-1]["assistant_slice"].strip())[0][:80] if spans else ""
            node_tag = f"（已关联 {', '.join(merged_nodes)}）" if merged_nodes else ""
            capsule_summary = f"{detail['title']}：{last_a}。{node_tag}"

        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        with self._connect() as conn:
            conn.execute(
                "UPDATE threads SET status = ?, capsule_summary = ?, title = COALESCE(?, title), updated_at = ? WHERE thread_id = ?",
                (status, capsule_summary.strip(), title.strip() if title else None, now, thread_id),
            )
            for nid in clean_nodes:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO thread_node_links(thread_id, node_id, provenance, confidence)
                    VALUES (?, ?, 'declared', 1.0)
                    """,
                    (thread_id, nid),
                )

        overrides = self._load_thread_state_overrides()
        cur = overrides.get(thread_id, {})
        cur["status"] = status
        cur["capsule_summary"] = capsule_summary.strip()
        if title:
            cur["title"] = title.strip()
        if merged_nodes:
            cur["node_refs"] = merged_nodes
        overrides[thread_id] = cur
        self._save_thread_state_overrides(overrides)
        return self.get_thread(thread_id) or {}

    def bind_threads_to_federated_graphs(self, federated: Mapping[str, Any]) -> None:
        """Infer high-confidence links between `THR-###` threads and `INT/SPEC/WP/KD` nodes."""
        with self._connect() as conn:
            threads = conn.execute("SELECT thread_id, title, centroid_blob FROM threads").fetchall()
            if not threads:
                return
            spans_by_thr: dict[str, list[sqlite3.Row]] = defaultdict(list)
            for r in conn.execute(
                """
                SELECT ts.thread_id, s.user_slice, s.assistant_slice, s.topic_hint
                FROM thread_spans ts
                JOIN spans s ON s.span_id = ts.span_id
                WHERE ts.role = 'primary'
                """
            ).fetchall():
                spans_by_thr[str(r["thread_id"])].append(r)

            # 1. Exact / substring utterance matching on Intent `raw_utterance`
            for inode in federated.get("intent", {}).get("nodes", []):
                iid = inode["id"]
                raw_u = re.sub(r"\s+", "", inode.get("raw_utterance", ""))
                if len(raw_u) < 8:
                    continue
                probe = raw_u[:22]
                for thr in threads:
                    tid = str(thr["thread_id"])
                    joined_u = re.sub(
                        r"\s+",
                        "",
                        " ".join(str(s["user_slice"]) for s in spans_by_thr.get(tid, ())),
                    )
                    if probe and probe in joined_u:
                        conn.execute(
                            """
                            INSERT OR IGNORE INTO thread_node_links(thread_id, node_id, provenance, confidence)
                            VALUES (?, ?, 'utterance_match', 0.96)
                            """,
                            (tid, iid),
                        )

            # 2. Canonical term / KD term anchor matching
            anchor_pairs: list[tuple[str, str]] = []
            for snode in federated.get("specs", {}).get("nodes", []):
                if snode.get("canonical_term"):
                    base_term = str(snode["canonical_term"]).split("(")[0].strip().lower()
                    if len(base_term) >= 4:
                        anchor_pairs.append((snode["id"], base_term))
                for fa in snode.get("forbidden_aliases") or []:
                    if len(str(fa).strip()) >= 4:
                        anchor_pairs.append((snode["id"], str(fa).strip().lower()))
            for kdnode in federated.get("knowledge_debt", {}).get("nodes", []):
                term_head = str(kdnode.get("term", "")).split("(")[0].strip().lower()
                if len(term_head) >= 5:
                    anchor_pairs.append((kdnode["id"], term_head))

            for thr in threads:
                tid = str(thr["thread_id"])
                blob_txt = " ".join(
                    f"{s['topic_hint']} {s['user_slice']} {s['assistant_slice']}"
                    for s in spans_by_thr.get(tid, ())
                ).lower()
                for nid, phrase in anchor_pairs:
                    if phrase in blob_txt:
                        conn.execute(
                            """
                            INSERT OR IGNORE INTO thread_node_links(thread_id, node_id, provenance, confidence)
                            VALUES (?, ?, 'anchor_match', 0.88)
                            """,
                            (tid, nid),
                        )

    def get_thread(self, thread_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            trow = conn.execute(
                "SELECT * FROM threads WHERE thread_id = ?", (thread_id,)
            ).fetchone()
            if not trow:
                return None
            srows = conn.execute(
                """
                SELECT s.*, ts.position, ts.role, ts.confidence,
                       t.session_id, t.turn_index, t.timestamp
                FROM thread_spans ts
                JOIN spans s ON s.span_id = ts.span_id
                JOIN turns t ON t.turn_id = s.turn_id
                WHERE ts.thread_id = ?
                ORDER BY t.turn_index ASC, s.span_index ASC
                """,
                (thread_id,),
            ).fetchall()
            lrows = conn.execute(
                "SELECT node_id, provenance, confidence FROM thread_node_links WHERE thread_id = ? ORDER BY node_id",
                (thread_id,),
            ).fetchall()
            xrows = conn.execute(
                """
                SELECT to_thread AS peer, via_span_id, 'outgoing' AS dir FROM thread_cross_refs WHERE from_thread = ?
                UNION ALL
                SELECT from_thread AS peer, via_span_id, 'incoming' AS dir FROM thread_cross_refs WHERE to_thread = ?
                """,
                (thread_id, thread_id),
            ).fetchall()

            return {
                "id": str(trow["thread_id"]),
                "title": str(trow["title"]),
                "status": str(trow["status"]),
                "capsule_summary": trow["capsule_summary"],
                "created_at": str(trow["created_at"]),
                "updated_at": str(trow["updated_at"]),
                "span_count": len(srows),
                "turn_count": len({str(r["turn_id"]) for r in srows}),
                "linked_nodes": [
                    {
                        "node_id": str(r["node_id"]),
                        "provenance": str(r["provenance"]),
                        "confidence": float(r["confidence"]),
                    }
                    for r in lrows
                ],
                "cross_threads": [
                    {
                        "thread_id": str(r["peer"]),
                        "via_span_id": str(r["via_span_id"]),
                        "direction": str(r["dir"]),
                    }
                    for r in xrows
                ],
                "spans": [
                    {
                        "span_id": str(r["span_id"]),
                        "turn_id": str(r["turn_id"]),
                        "session_id": str(r["session_id"]),
                        "turn_index": int(r["turn_index"]),
                        "timestamp": str(r["timestamp"]),
                        "span_index": int(r["span_index"]),
                        "span_total": int(r["span_total"]),
                        "role": str(r["role"]),
                        "topic_hint": str(r["topic_hint"]),
                        "user_slice": str(r["user_slice"]),
                        "assistant_slice": str(r["assistant_slice"]),
                        "user_char_range": [int(r["user_char_start"]), int(r["user_char_end"])],
                        "asst_char_range": [int(r["asst_char_start"]), int(r["asst_char_end"])],
                    }
                    for r in srows
                ],
            }

    def list_threads(self, include_spans: bool = True) -> list[dict[str, Any]]:
        with self._connect() as conn:
            tids = [
                str(r["thread_id"])
                for r in conn.execute("SELECT thread_id FROM threads ORDER BY thread_id").fetchall()
            ]
        out: list[dict[str, Any]] = []
        for tid in tids:
            th = self.get_thread(tid)
            if th is None:
                continue
            if not include_spans:
                th = {k: v for k, v in th.items() if k != "spans"}
            out.append(th)
        return out

    def search_spans(self, query_text: str, top_k: int = 8) -> dict[str, Any]:
        """Hybrid SQLite FTS5 BM25 + dense vector cosine search across atomic sub-turn Spans."""
        q_clean = query_text.strip()
        if not q_clean:
            return {"query": query_text, "results": []}

        q_vec = self._embed([q_clean], True, False)[0]
        q_toks = _extract_lexical_tokens(q_clean)

        fts_ranks: dict[str, float] = {}
        with self._connect() as conn:
            if self.has_fts5:
                fts_tokens = [
                    re.sub(r'["\'*^():-]', "", tok)
                    for tok in re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]+", q_clean)
                ]
                fts_tokens = [t for t in fts_tokens if t]
                if fts_tokens:
                    fts_expr = " OR ".join(f'"{t}"' for t in fts_tokens[:8])
                    try:
                        frows = conn.execute(
                            "SELECT span_id, bm25(spans_fts) AS score FROM spans_fts WHERE spans_fts MATCH ? LIMIT 30",
                            (fts_expr,),
                        ).fetchall()
                        for rank_idx, fr in enumerate(frows):
                            fts_ranks[str(fr["span_id"])] = round(1.0 / (1.0 + rank_idx * 0.25), 4)
                    except sqlite3.OperationalError:
                        pass

            srows = conn.execute(
                """
                SELECT s.*, t.session_id, t.turn_index, t.timestamp
                FROM spans s
                JOIN turns t ON t.turn_id = s.turn_id
                """
            ).fetchall()
            if not srows:
                return {"query": query_text, "results": []}

            thr_map: dict[str, list[str]] = defaultdict(list)
            for tr in conn.execute("SELECT span_id, thread_id FROM thread_spans ORDER BY role").fetchall():
                thr_map[str(tr["span_id"])].append(str(tr["thread_id"]))

            node_map: dict[str, list[str]] = defaultdict(list)
            for nr in conn.execute("SELECT thread_id, node_id FROM thread_node_links ORDER BY node_id").fetchall():
                node_map[str(nr["thread_id"])].append(str(nr["node_id"]))

            thr_titles = {
                str(r["thread_id"]): (str(r["title"]), str(r["status"]))
                for r in conn.execute("SELECT thread_id, title, status FROM threads").fetchall()
            }

        is_dense = self.backend_name in {"mlx", "openai"}
        if self.embed_fn is not None:
            span_doc_texts = [
                f"[Dialogue Span: {r['topic_hint']}] User: {r['user_slice']}\nAssistant: {r['assistant_slice']}"
                for r in srows
            ]
            resolved_span_vecs = self._embed(span_doc_texts, False, True)
        else:
            resolved_span_vecs = [
                unpack_f32(r["vec_blob"]) if r["vec_blob"] else []
                for r in srows
            ]

        scored: list[dict[str, Any]] = []
        for r, s_vec in zip(srows, resolved_span_vecs):
            sid = str(r["span_id"])
            raw_sim = _cosine(q_vec, s_vec) if s_vec else 0.0
            norm_sim = (
                max(0.0, (raw_sim + 1.0) / 2.0)
                if is_dense
                else max(0.0, raw_sim)
            )
            s_toks = _extract_lexical_tokens(
                f"{r['topic_hint']} {r['user_slice']} {r['assistant_slice']}"
            )
            kw_ov = len(q_toks & s_toks) / max(1, len(q_toks)) if q_toks and s_toks else 0.0
            fts_bonus = fts_ranks.get(sid, 0.0)
            final_score = round(0.62 * norm_sim + 0.24 * kw_ov + 0.22 * fts_bonus, 4)

            tids = thr_map.get(sid, [])
            primary_tid = tids[0] if tids else None
            t_title, t_status = thr_titles.get(primary_tid or "", ("", ""))
            linked_nodes = sorted({nid for tid in tids for nid in node_map.get(tid, ())})

            scored.append(
                {
                    "span_id": sid,
                    "turn_id": str(r["turn_id"]),
                    "turn_index": int(r["turn_index"]),
                    "span_position_in_turn": f"{r['span_index']}/{r['span_total']}",
                    "thread_id": primary_tid,
                    "thread_title": t_title,
                    "thread_status": t_status,
                    "all_threads": tids,
                    "linked_nodes": linked_nodes,
                    "topic_hint": str(r["topic_hint"]),
                    "user_slice": str(r["user_slice"]),
                    "assistant_slice": str(r["assistant_slice"]),
                    "semantic_similarity": round(raw_sim, 4),
                    "fts5_score": fts_bonus,
                    "combined_score": final_score,
                }
            )

        scored.sort(key=lambda x: (-x["combined_score"], -x["semantic_similarity"], x["span_id"]))
        return {
            "query": query_text,
            "fts5_enabled": self.has_fts5,
            "embedding_backend": self.backend_name,
            "results": scored[:top_k],
        }

    def render_selective_context(self) -> dict[str, Any]:
        """Render Per-Thread Selective Context: full spans for `active`, 1-line capsules for `folded`."""
        threads = self.list_threads(include_spans=True)
        active_blocks: list[dict[str, Any]] = []
        folded_capsules: list[dict[str, Any]] = []
        raw_chars = 0
        selective_chars = 0

        for th in threads:
            full_txt = "\n".join(
                f"U: {s['user_slice']}\nA: {s['assistant_slice']}" for s in th["spans"]
            )
            raw_chars += len(full_txt)
            nodes_str = ", ".join(x["node_id"] for x in th["linked_nodes"])
            if th["status"] in {"folded", "crystallized", "resolved"} and th.get("capsule_summary"):
                cap_line = (
                    f"[{th['id']} · {th['status']}"
                    + (f" -> {nodes_str}" if nodes_str else "")
                    + f"] {th['capsule_summary']} (共 {th['span_count']} 段切片已归档于 memory.sqlite)"
                )
                selective_chars += len(cap_line)
                folded_capsules.append(
                    {
                        "thread_id": th["id"],
                        "title": th["title"],
                        "status": th["status"],
                        "linked_nodes": [x["node_id"] for x in th["linked_nodes"]],
                        "span_count": th["span_count"],
                        "capsule_line": cap_line,
                    }
                )
            else:
                selective_chars += len(full_txt)
                active_blocks.append(
                    {
                        "thread_id": th["id"],
                        "title": th["title"],
                        "status": th["status"],
                        "linked_nodes": [x["node_id"] for x in th["linked_nodes"]],
                        "spans": [
                            {
                                "span_id": s["span_id"],
                                "turn_id": s["turn_id"],
                                "in_turn": f"{s['span_index']}/{s['span_total']}",
                                "user": s["user_slice"],
                                "assistant": s["assistant_slice"],
                            }
                            for s in th["spans"]
                        ],
                    }
                )

        saved_ratio = (
            round(1.0 - (selective_chars / raw_chars), 4)
            if raw_chars > 0 and selective_chars <= raw_chars
            else 0.0
        )
        return {
            "schema_version": MEMORY_SCHEMA,
            "db_path": str(self.db_path),
            "active_thread_count": len(active_blocks),
            "folded_thread_count": len(folded_capsules),
            "raw_dialogue_chars": raw_chars,
            "selective_context_chars": selective_chars,
            "char_compression_ratio": saved_ratio,
            "folded_capsules": folded_capsules,
            "active_threads": active_blocks,
        }

    def export_summary(self) -> dict[str, Any]:
        with self._connect() as conn:
            turn_cnt = int(conn.execute("SELECT COUNT(*) FROM turns").fetchone()[0])
            span_cnt = int(conn.execute("SELECT COUNT(*) FROM spans").fetchone()[0])
            vec_cnt = int(conn.execute("SELECT COUNT(*) FROM vector_cache").fetchone()[0])
        threads = self.list_threads(include_spans=True)
        return {
            "schema_version": MEMORY_SCHEMA,
            "db_path": self.db_path.relative_to(self.repo_root).as_posix(),
            "fts5_enabled": self.has_fts5,
            "turn_count": turn_cnt,
            "span_count": span_cnt,
            "thread_count": len(threads),
            "vector_blob_count": vec_cnt,
            "folded_count": sum(
                1 for t in threads if t["status"] in {"folded", "crystallized", "resolved"}
            ),
            "active_count": sum(1 for t in threads if t["status"] == "active"),
            "threads": threads,
        }


def attach_episodic_threads_to_federated(
    federated: dict[str, Any], ep_summary: Mapping[str, Any]
) -> None:
    """Attach disentangled `THR-###` thread records onto linked Intent, Spec, Plan, and KD nodes."""
    threads_by_node: dict[str, list[dict[str, Any]]] = defaultdict(list)
    threads_by_id: dict[str, dict[str, Any]] = {}
    for th in ep_summary.get("threads", []):
        threads_by_id[th["id"]] = th
        for lnk in th.get("linked_nodes", []):
            threads_by_node[lnk["node_id"]].append(th)

    for gkey in ("intent", "specs", "plan", "knowledge_debt"):
        for n in federated.get(gkey, {}).get("nodes", []):
            nid = n["id"]
            linked = {t["id"]: t for t in threads_by_node.get(nid, [])}
            for explicit_tid in n.get("thread_refs", []) or []:
                if explicit_tid in threads_by_id:
                    linked[explicit_tid] = threads_by_id[explicit_tid]
            ordered = [linked[k] for k in sorted(linked)]
            n["episodic_threads"] = ordered
            n["episodic_rollup"] = {
                "thread_count": len(ordered),
                "thread_ids": [t["id"] for t in ordered],
                "span_count": sum(t.get("span_count", 0) for t in ordered),
                "active_count": sum(1 for t in ordered if t.get("status") == "active"),
                "folded_count": sum(
                    1 for t in ordered if t.get("status") in {"folded", "crystallized", "resolved"}
                ),
            }
    federated["episodic_memory"] = dict(ep_summary)
