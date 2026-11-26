#!/usr/bin/env python3
"""On-device Embedding + Hebbian Associative Memory Engine for PtM.

Inspired by cognitive neuroscience and HeLa-Mem (Zhu et al., ACL 2026), upgraded for
PtM's federated four-graph architecture:
- Apple Silicon SOTA local embeddings via `mlx-community/Qwen3-Embedding-0.6B-4bit-DWQ`
  (`mlx-embeddings`), with automatic `.venv` bridge, content-addressed disk cache, and
  deterministic stdlib subword-hash fallback for offline/cross-platform tests.
- Strict edge provenance: associative weights live in `_aiHumanInteract/hebbian/associations.json`
  (`"provenance": "associative"`) and never overwrite Declared or Observed structural edges.
- Dual-Path Retrieval (`Base Top-k + Spreading Activation Flip Top-m`) with full
  spreading-source trace, valid ISO-date recency, and Hub Detection.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from ptm_memory import (
    EpisodicMemoryStore,
    SqliteVectorStore,
    attach_episodic_threads_to_federated,
)

SKILL_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MLX_MODEL = "mlx-community/Qwen3-Embedding-0.6B-4bit-DWQ"
OPENAI_BATCH_SIZE = 10
OPENAI_TIMEOUT_SECONDS = 30.0
DENSE_BACKENDS = {"mlx", "openai"}
BACKEND_CHOICES = ("auto", "mlx", "local", "openai", "api", "hash")
HEBBIAN_SCHEMA = "paths-to-modernity-hebbian-associative-v1"
QUERY_INSTRUCTION = (
    "Instruct: Retrieve semantically or associatively related project intents, "
    "concepts, plans, knowledge-debt bookmarks, and source scripts\nQuery: "
)

TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_.-]{1,}|[\u4e00-\u9fff]{1,}")

_MLX_CACHE: dict[str, tuple[Any, Any]] = {}


def _l2_normalize(vec: Sequence[float]) -> list[float]:
    norm = math.sqrt(sum(float(x) * float(x) for x in vec))
    if norm <= 1e-12:
        return [0.0 for _ in vec]
    return [round(float(x) / norm, 6) for x in vec]


def _dot(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b):
        return 0.0
    return sum(x * y for x, y in zip(a, b))


def _extract_keywords(text: str) -> set[str]:
    """Fast deterministic bilingual + code keyword extractor (no per-node LLM overhead)."""
    kws: set[str] = set()
    for match in TOKEN_RE.finditer(text.lower()):
        tok = match.group(0)
        if "\u4e00" <= tok[0] <= "\u9fff":
            if len(tok) <= 4:
                kws.add(tok)
            for i in range(len(tok) - 1):
                kws.add(tok[i : i + 2])
        elif len(tok) >= 3 and tok not in {
            "the", "and", "for", "with", "that", "this", "from", "into", "when", "none",
        }:
            kws.add(tok)
    return kws


def _stdlib_hash_embed(text: str, dim: int = 384) -> list[float]:
    """Deterministic subword + character n-gram L2 embedding using pure Python stdlib."""
    vec = [0.0] * dim
    clean = re.sub(r"\s+", " ", text.lower()).strip()
    if not clean:
        return vec
    features: list[tuple[str, float]] = []
    for kw in _extract_keywords(clean):
        features.append((f"w:{kw}", 2.2))
    for n in (2, 3, 4):
        for i in range(max(0, len(clean) - n + 1)):
            gram = clean[i : i + n]
            if gram.strip():
                features.append((f"c{n}:{gram}", 0.7 if n > 2 else 0.5))
    for feat, weight in features:
        digest = hashlib.blake2b(feat.encode("utf-8"), digest_size=8).digest()
        idx = int.from_bytes(digest[:4], "little") % dim
        sign = 1.0 if (digest[4] & 1) == 0 else -1.0
        vec[idx] += sign * weight
    return _l2_normalize(vec)


def _embed_with_mlx_inproc(texts: Sequence[str], model_id: str) -> list[list[float]]:
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    import mlx.core as mx
    from mlx_embeddings import generate, load

    if model_id not in _MLX_CACHE:
        _MLX_CACHE[model_id] = load(model_id)
    model, tokenizer = _MLX_CACHE[model_id]
    results: list[list[float]] = []
    batch_size = 16
    for i in range(0, len(texts), batch_size):
        batch = list(texts[i : i + batch_size])
        out = generate(model, tokenizer, batch, max_length=1024)
        arr = out.text_embeds.astype(mx.float32).tolist()
        for row in arr:
            results.append(_l2_normalize(row))
    return results


def _normalize_backend_choice(backend: str) -> str:
    raw = (backend or "auto").strip().lower()
    if raw == "local":
        return "mlx"
    if raw == "api":
        return "openai"
    if raw in {"auto", "mlx", "openai", "hash"}:
        return raw
    raise RuntimeError(f"Unsupported embedding backend {backend!r}; expected one of {BACKEND_CHOICES}.")


def _local_mlx_model() -> str:
    return os.environ.get("PTM_EMBEDDING_LOCAL_MODEL", "").strip() or DEFAULT_MLX_MODEL


def _probe_python_mlx(py_bin: Path | str) -> bool:
    res = subprocess.run(
        [str(py_bin), "-c", "import mlx_embeddings"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return res.returncode == 0


def _detect_mlx_python(*, explicit_only: bool = False) -> str | None:
    """Return path to Python interpreter with `mlx_embeddings`, checking env, current, `.venv`, and source manifest."""
    env_py = os.environ.get("PTM_EMBEDDING_LOCAL_PYTHON", "").strip()
    if env_py:
        cand = Path(env_py).expanduser()
        if cand.is_file() and _probe_python_mlx(cand):
            return str(cand)
        if explicit_only:
            raise RuntimeError(
                f"Configured PTM_EMBEDDING_LOCAL_PYTHON={env_py!r} does not exist or cannot import mlx_embeddings."
            )
        return None

    try:
        import mlx_embeddings  # noqa: F401
        return sys.executable
    except ImportError:
        pass

    candidates: list[Path] = [SKILL_ROOT / ".venv" / "bin" / "python"]
    manifest_file = SKILL_ROOT / ".sync-manifest.json"
    if manifest_file.is_file():
        try:
            src_str = json.loads(manifest_file.read_text(encoding="utf-8")).get("source", "")
            if src_str:
                candidates.append(Path(src_str) / ".venv" / "bin" / "python")
        except (OSError, json.JSONDecodeError):
            pass
    for ancestor in SKILL_ROOT.parents:
        candidates.append(ancestor / "skills" / "paths-to-modernity" / ".venv" / "bin" / "python")

    seen: set[str] = set()
    for venv_py in candidates:
        key = str(venv_py)
        if key in seen:
            continue
        seen.add(key)
        if venv_py.is_file() and _probe_python_mlx(venv_py):
            return key
    return None


def _openai_embedding_config() -> dict[str, Any] | None:
    """Read OpenAI-compatible embedding config from `PTM_EMBEDDING_*` env vars.

    Opt-in only: `auto` never implicitly invokes `openai`, so an ambient API key
    cannot turn an offline build into a billed network call.
    """
    base_url = os.environ.get("PTM_EMBEDDING_BASE_URL", "").strip().rstrip("/")
    model = os.environ.get("PTM_EMBEDDING_MODEL", "").strip()
    api_key = os.environ.get("PTM_EMBEDDING_API_KEY", "").strip()
    if not (base_url and model and api_key):
        return None
    raw_dimensions = os.environ.get("PTM_EMBEDDING_DIMENSIONS", "").strip()
    dimensions = (
        int(raw_dimensions)
        if raw_dimensions.isdigit() and int(raw_dimensions) > 0
        else None
    )
    raw_timeout = os.environ.get("PTM_EMBEDDING_TIMEOUT", "").strip()
    try:
        timeout = float(raw_timeout) if raw_timeout else OPENAI_TIMEOUT_SECONDS
    except ValueError:
        timeout = OPENAI_TIMEOUT_SECONDS
    return {
        "base_url": base_url,
        "model": model,
        "api_key": api_key,
        "dimensions": dimensions,
        "timeout": timeout,
    }


def _embed_with_openai(texts: Sequence[str], config: Mapping[str, Any]) -> list[list[float]]:
    """Embed texts via an OpenAI-compatible `/embeddings` endpoint with strict dimension & HTTP checks."""
    vectors: list[list[float]] = []
    url = f"{config['base_url']}/embeddings"
    for start in range(0, len(texts), OPENAI_BATCH_SIZE):
        batch = list(texts[start : start + OPENAI_BATCH_SIZE])
        payload: dict[str, Any] = {
            "model": config["model"],
            "input": batch,
            "encoding_format": "float",
        }
        if config.get("dimensions"):
            payload["dimensions"] = int(config["dimensions"])
        request = urllib.request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {config['api_key']}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=float(config["timeout"])) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:500]
            raise RuntimeError(
                f"embedding API {url} returned HTTP {exc.code}: {detail}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"embedding API {url} request failed: {exc.reason}"
            ) from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"embedding API {url} returned a non-JSON body"
            ) from exc

        data = body.get("data")
        if not isinstance(data, list) or len(data) != len(batch):
            raise RuntimeError(
                f"embedding API {url} returned {len(data) if isinstance(data, list) else 'no'} "
                f"vectors for {len(batch)} inputs"
            )
        ordered = sorted(
            data,
            key=lambda row: row.get("index", 0) if isinstance(row, Mapping) else 0,
        )
        for row in ordered:
            vector = row.get("embedding") if isinstance(row, Mapping) else None
            if not isinstance(vector, list) or not vector:
                raise RuntimeError(f"embedding API {url} returned an empty embedding")
            if config.get("dimensions") and len(vector) != int(config["dimensions"]):
                raise RuntimeError(
                    f"embedding API {url} returned {len(vector)} dimensions, "
                    f"expected {config['dimensions']}"
                )
            vectors.append(_l2_normalize(vector))
    return vectors


class TieredEmbedder:
    """Content-addressed dual-interface embedder (`mlx` local + `openai` API + `hash`) over SQLite float32 BLOBs."""

    def __init__(
        self,
        cache_path: Path,
        backend: str = "auto",
        model_id: str | None = None,
    ) -> None:
        self.cache_path = cache_path
        self.requested_backend = backend
        norm_backend = _normalize_backend_choice(backend)
        self.model_id = (model_id or "").strip() or _local_mlx_model()
        self.openai_config = _openai_embedding_config()
        self.active_backend, self.mlx_python = self._resolve_backend(norm_backend)
        if self.active_backend == "mlx":
            self.effective_model_id = (
                self.model_id if self.model_id.startswith("mlx:") else f"mlx:{self.model_id}"
            )
        elif self.active_backend == "openai":
            assert self.openai_config is not None
            dimensions = self.openai_config.get("dimensions") or "default"
            self.effective_model_id = f"openai:{self.openai_config['model']}:{dimensions}"
        else:
            self.effective_model_id = "ptm-stdlib-ngram-384"

        db_file = (
            cache_path
            if cache_path.suffix in {".sqlite", ".db"}
            else cache_path.parent / "memory.sqlite"
        )
        legacy_json = (
            cache_path
            if cache_path.suffix == ".json"
            else cache_path.parent / "embeddings.json"
        )
        self._sql_store = SqliteVectorStore(db_file, legacy_json_path=legacy_json)
        self._mem_cache: dict[str, list[float]] = {}

    def _resolve_backend(self, backend: str) -> tuple[str, str | None]:
        if backend == "hash":
            return "hash", None
        if backend == "openai":
            if not self.openai_config:
                raise RuntimeError(
                    "OpenAI embedding backend requested, but PTM_EMBEDDING_BASE_URL, "
                    "PTM_EMBEDDING_MODEL, and PTM_EMBEDDING_API_KEY are not all set."
                )
            return "openai", None
        if backend == "mlx":
            mlx_py = _detect_mlx_python(explicit_only=True)
            if not mlx_py:
                raise RuntimeError(
                    "Local MLX backend requested, but mlx-embeddings is not installed in Python or .venv."
                )
            return "mlx", mlx_py
        mlx_py = _detect_mlx_python(explicit_only=False)
        if mlx_py:
            return "mlx", mlx_py
        return "hash", None

    def _key(self, text: str) -> str:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:24]
        return f"{self.effective_model_id}:{digest}"

    def embed_many(
        self,
        texts: Sequence[str],
        *,
        is_query: bool = False,
        persist_cache: bool = True,
    ) -> list[list[float]]:
        if not texts:
            return []
        raw_mlx_model = (
            self.model_id[4:] if self.model_id.startswith("mlx:") else self.model_id
        )
        formatted = [
            (QUERY_INSTRUCTION + t if (is_query and self.active_backend == "mlx") else t)
            for t in texts
        ]
        keys = [self._key(t) for t in formatted]
        need_db = [k for k in keys if k not in self._mem_cache]
        if need_db:
            loaded = self._sql_store.get_many(need_db)
            self._mem_cache.update(loaded)

        missing_indices = [i for i, k in enumerate(keys) if k not in self._mem_cache]
        if missing_indices:
            missing_texts = [formatted[i] for i in missing_indices]
            if self.active_backend == "mlx":
                if self.mlx_python == sys.executable:
                    computed = _embed_with_mlx_inproc(missing_texts, raw_mlx_model)
                else:
                    helper = (
                        "import json, os, sys; os.environ['HF_HUB_DISABLE_PROGRESS_BARS']='1'; "
                        f"sys.path.insert(0, {json.dumps(str(SKILL_ROOT / 'scripts'))}); "
                        "from ptm_hebbian import _embed_with_mlx_inproc; "
                        "req = json.loads(sys.stdin.read()); "
                        "vecs = _embed_with_mlx_inproc(req['texts'], req['model']); "
                        "sys.stdout.write(json.dumps(vecs))"
                    )
                    proc = subprocess.run(
                        [str(self.mlx_python), "-c", helper],
                        input=json.dumps({"texts": missing_texts, "model": raw_mlx_model}),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        check=True,
                    )
                    computed = json.loads(proc.stdout)
            elif self.active_backend == "openai":
                assert self.openai_config is not None
                computed = _embed_with_openai(missing_texts, self.openai_config)
            else:
                computed = [_stdlib_hash_embed(t) for t in missing_texts]

            ephemeral: dict[int, list[float]] = {}
            to_persist: dict[str, list[float]] = {}
            for idx, vec in zip(missing_indices, computed):
                if persist_cache:
                    self._mem_cache[keys[idx]] = vec
                    to_persist[keys[idx]] = vec
                else:
                    ephemeral[idx] = vec
            if persist_cache and to_persist:
                self._sql_store.put_many(self.effective_model_id, to_persist)
            elif not persist_cache:
                return [
                    self._mem_cache[k] if k in self._mem_cache else ephemeral[i]
                    for i, k in enumerate(keys)
                ]

        return [self._mem_cache[k] for k in keys]

    def probe(self) -> dict[str, Any]:
        """Run a two-sentence non-persisted smoke probe and return structured runtime telemetry."""
        t0 = time.perf_counter()
        vecs = self.embed_many(
            ["PtM 双接口嵌入自检", "Cross-graph associative embedding probe"],
            is_query=False,
            persist_cache=False,
        )
        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        return {
            "ok": True,
            "requested_backend": self.requested_backend,
            "active_backend": self.active_backend,
            "effective_model_id": self.effective_model_id,
            "dimensions": len(vecs[0]) if vecs else 0,
            "python": self.mlx_python,
            "latency_ms": elapsed_ms,
        }


def _compute_recency(updated_str: str | None, ref_date: date, tau_days: float = 120.0) -> float:
    """Valid ISO-8601 date temporal decay in (0.5, 1.0]. Fixes HeLa-Mem's silent TypeError."""
    if not updated_str:
        return 1.0
    try:
        d = date.fromisoformat(updated_str[:10])
        delta_days = max(0.0, float((ref_date - d).days))
        # Soft floor at 0.65 so foundational architectural intents/plans don't vanish
        return 0.65 + 0.35 * math.exp(-delta_days / max(1.0, tau_days))
    except ValueError:
        return 1.0


def _eval_context_snippet(node: Mapping[str, Any]) -> str:
    evals = node.get("evaluations") or []
    if not evals:
        return ""
    parts = []
    for ev in evals:
        risks = "; ".join(ev.get("at_risk_qualities") or [])
        pres = "; ".join(ev.get("preserved_qualities") or [])
        parts.append(
            f"[Eval {ev['id']} {ev['verdict']} · {ev['perspective']}] {ev['summary']}"
            + (f" Preserved: {pres}." if pres else "")
            + (f" At-risk: {risks}." if risks else "")
        )
    return " Evaluations: " + " | ".join(parts)


def _unified_nodes_from_federated(federated: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Convert all 5 federated graphs into rich textual descriptors for associative indexing."""
    unified: list[dict[str, Any]] = []

    for n in federated.get("intent", {}).get("nodes", []):
        concepts_txt = "; ".join(
            f"{c.get('name', '')}: {c.get('definition', '')} "
            + " | ".join(v.get("meaning", "") for v in c.get("interpretive_variants", []))
            for c in n.get("concepts", [])
        )
        alts_txt = "; ".join(
            a.get("approach", "") for a in n.get("implementation_alternatives", [])
        )
        text = (
            f"[Intent {n['id']}] {n['title']}. Raw user intent: {n['raw_utterance']}. "
            f"Concepts & variants: {concepts_txt}. Alternatives: {alts_txt}. "
            f"Qualities: {'; '.join(n.get('qualities', []))}."
            + _eval_context_snippet(n)
        )
        unified.append(
            {
                "id": n["id"],
                "graph": "intent",
                "title": n["title"],
                "status": n["status"],
                "updated": n.get("updated", ""),
                "text": text,
                "keywords": sorted(_extract_keywords(text)),
            }
        )

    for n in federated.get("specs", {}).get("nodes", []):
        aliases = ", ".join(n.get("forbidden_aliases") or [])
        dos = "; ".join(n.get("do_rules") or [])
        donts = "; ".join(n.get("dont_rules") or [])
        posts = "; ".join(n.get("postconditions") or [])
        text = (
            f"[Spec {n['id']} ({n['kind']} · {n['enforcement']})] {n['title']}. "
            f"Summary: {n['summary']} "
            f"Canonical term: {n.get('canonical_term') or ''}. "
            f"Forbidden aliases: {aliases}. "
            f"DO: {dos}. DO NOT: {donts}. "
            f"Contract/Schema: {n.get('signature_or_schema') or ''}. "
            f"Postconditions: {posts}."
            + _eval_context_snippet(n)
        )
        kws = _extract_keywords(text)
        if n.get("canonical_term"):
            kws |= _extract_keywords(str(n["canonical_term"]))
        for fa in n.get("forbidden_aliases") or []:
            kws.add(str(fa).strip().lower())
            kws |= _extract_keywords(str(fa))
        unified.append(
            {
                "id": n["id"],
                "graph": "specs",
                "title": n["title"],
                "status": n["status"],
                "updated": n.get("updated", ""),
                "text": text,
                "keywords": sorted(kws),
            }
        )

    for n in federated.get("plan", {}).get("nodes", []):
        ctx = n.get("context") or {}
        text = (
            f"[Plan {n['id']} ({n['level']})] {n['title']}. Objective: {n['objective']} "
            f"Deliverables: {'; '.join(n.get('deliverables', []))}. "
            f"Acceptance: {'; '.join(n.get('acceptance', []))}. "
            f"Approach: {n.get('approach', '')}. Problem: {ctx.get('problem', '')}. "
            f"Qualities: {'; '.join(n.get('qualities', []))}."
            + _eval_context_snippet(n)
        )
        unified.append(
            {
                "id": n["id"],
                "graph": "plan",
                "title": n["title"],
                "status": n["status"],
                "updated": n.get("updated", ""),
                "text": text,
                "keywords": sorted(_extract_keywords(text)),
            }
        )

    for n in federated.get("knowledge_debt", {}).get("nodes", []):
        text = (
            f"[KnowledgeDebt {n['id']}] {n['term']} ({n['kind']}, {n['status']}). "
            f"Revisit when: {n['revisit_when']}. "
            f"Counterproposal: {n.get('counterproposal') or ''}."
        )
        unified.append(
            {
                "id": n["id"],
                "graph": "knowledge_debt",
                "title": n["term"],
                "status": n["status"],
                "updated": n.get("updated", ""),
                "text": text,
                "keywords": sorted(_extract_keywords(text)),
            }
        )

    for n in federated.get("scripts", {}).get("nodes", []):
        syms = ", ".join([*n.get("classes", []), *n.get("functions", [])][:12])
        text = (
            f"[Script {n['path']}] ({n['language']} {n['role']}). "
            f"Summary: {n.get('summary', '')}. Symbols: {syms}."
        )
        unified.append(
            {
                "id": n["id"],
                "graph": "scripts",
                "title": n["path"],
                "status": n["status"],
                "updated": "",
                "text": text,
                "keywords": sorted(_extract_keywords(text)),
            }
        )

    return unified


class HebbianAssociativeEngine:
    """Manages cross-graph embeddings, Hebbian synapses, hub detection, and Dual-Path retrieval."""

    def __init__(
        self,
        repo_root: Path,
        *,
        backend: str = "auto",
        learning_rate: float = 0.06,
        decay_rate: float = 0.992,
        spreading_beta: float = 0.22,
        spreading_threshold: float = 0.35,
        hub_threshold: float = 1.15,
    ) -> None:
        self.repo_root = repo_root.resolve()
        self.assoc_path = (
            self.repo_root / "_aiHumanInteract" / "hebbian" / "associations.json"
        )
        self.cache_path = (
            self.repo_root / "_aiHumanInteract" / ".cache" / "memory.sqlite"
        )
        self.embedder = TieredEmbedder(self.cache_path, backend=backend)
        self.learning_rate = learning_rate
        self.decay_rate = decay_rate
        self.spreading_beta = spreading_beta
        self.spreading_threshold = spreading_threshold
        self.hub_threshold = hub_threshold

        self.nodes: dict[str, dict[str, Any]] = {}
        self.vectors: dict[str, list[float]] = {}
        # Symmetric associative weights: edges[u][v] = {"weight": float, "coactivations": int, "origin": str}
        self.synapses: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
        self.access_counts: dict[str, int] = defaultdict(int)
        self.last_activated: dict[str, str] = {}
        self.coactivation_events: list[dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        if not self.assoc_path.is_file():
            return
        try:
            data = json.loads(self.assoc_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        self.access_counts.update(
            {k: int(v) for k, v in data.get("access_counts", {}).items()}
        )
        self.last_activated.update(data.get("last_activated", {}))
        self.coactivation_events = list(data.get("coactivation_events", []))[-50:]
        for edge in data.get("synapses", []):
            u, v = edge["from"], edge["to"]
            rec = {
                "weight": float(edge["weight"]),
                "coactivations": int(edge.get("coactivations", 0)),
                "similarity": float(edge.get("similarity", 0.0)),
                "origin": edge.get("origin", "semantic_seed"),
            }
            self.synapses[u][v] = dict(rec)
            self.synapses[v][u] = dict(rec)

    def make_episodic_store(self) -> EpisodicMemoryStore:
        """Create an `EpisodicMemoryStore` sharing this engine's active embedder & `memory.sqlite`."""
        return EpisodicMemoryStore(
            self.repo_root,
            embed_fn=lambda texts, is_q, persist: self.embedder.embed_many(
                texts, is_query=is_q, persist_cache=persist
            ),
            backend_name=self.embedder.active_backend,
            effective_model_id=self.embedder.effective_model_id,
        )

    def sync_federated(
        self, federated: Mapping[str, Any], *, persist: bool = True
    ) -> dict[str, Any]:
        """Embed all current nodes across the 5 graphs, sync episodic threads, and seed synapses."""
        if persist and (
            (self.repo_root / "_aiHumanInteract" / "episodes" / "turns.jsonl").is_file()
            or (self.repo_root / "_aiHumanInteract" / ".cache" / "memory.sqlite").is_file()
        ):
            ep_store = self.make_episodic_store()
            ep_sum = ep_store.sync_portable_episodes(federated)
            if isinstance(federated, dict):
                attach_episodic_threads_to_federated(federated, ep_sum)
        unified = _unified_nodes_from_federated(federated)
        self.nodes = {item["id"]: item for item in unified}
        valid_ids = set(self.nodes)

        # Prune stale node IDs that no longer exist in any graph
        for u in list(self.synapses):
            if u not in valid_ids:
                del self.synapses[u]
            else:
                for v in list(self.synapses[u]):
                    if v not in valid_ids:
                        del self.synapses[u][v]

        ordered_ids = sorted(self.nodes)
        if not ordered_ids:
            return self.export_payload()

        vecs = self.embedder.embed_many(
            [self.nodes[nid]["text"] for nid in ordered_ids],
            is_query=False,
            persist_cache=persist,
        )
        self.vectors = dict(zip(ordered_ids, vecs))

        # Collect structural pairs so we distinguish novel associative bridges from declared links
        declared_pairs: set[tuple[str, str]] = set()
        for gname in ("intent", "specs", "plan", "knowledge_debt", "scripts"):
            for e in federated.get(gname, {}).get("edges", []):
                declared_pairs.add((e["from"], e["to"]))
                declared_pairs.add((e["to"], e["from"]))
        for e in federated.get("cross_edges", []):
            declared_pairs.add((e["from"], e["to"]))
            declared_pairs.add((e["to"], e["from"]))

        seed_thresh = 0.44 if self.embedder.active_backend in DENSE_BACKENDS else 0.26

        # Pairwise semantic seeding (keeps top-4 strongest semantic neighbors per node)
        for i, u in enumerate(ordered_ids):
            candidates: list[tuple[float, str]] = []
            vu = self.vectors[u]
            for j, v in enumerate(ordered_ids):
                if i == j:
                    continue
                sim = _dot(vu, self.vectors[v])
                if sim >= seed_thresh:
                    candidates.append((sim, v))
            candidates.sort(reverse=True)
            for sim, v in candidates[:4]:
                existing = self.synapses[u].get(v)
                seed_w = round(min(0.48, max(0.08, (sim - seed_thresh + 0.12) * 0.75)), 4)
                if existing is None:
                    rec = {
                        "weight": seed_w,
                        "coactivations": 0,
                        "similarity": round(sim, 4),
                        "origin": "cross_graph_seed"
                        if self.nodes[u]["graph"] != self.nodes[v]["graph"]
                        else "semantic_seed",
                    }
                    self.synapses[u][v] = dict(rec)
                    self.synapses[v][u] = dict(rec)
                else:
                    existing["similarity"] = round(sim, 4)
                    self.synapses[v][u]["similarity"] = round(sim, 4)

        # Gentle structural-context co-activation seed along cross-graph Intent <-> Plan <-> KD triads
        for e in federated.get("cross_edges", []):
            u, v = e["from"], e["to"]
            if u in valid_ids and v in valid_ids and u != v:
                sim = _dot(self.vectors[u], self.vectors[v])
                cur = self.synapses[u].get(v)
                base_w = max(cur["weight"] if cur else 0.0, 0.32)
                rec = {
                    "weight": round(min(1.0, base_w), 4),
                    "coactivations": cur["coactivations"] if cur else 1,
                    "similarity": round(sim, 4),
                    "origin": cur["origin"] if cur else "cross_graph_link",
                }
                self.synapses[u][v] = dict(rec)
                self.synapses[v][u] = dict(rec)

        if persist and isinstance(federated, dict) and "episodic_memory" in federated:
            ep_sum_after = self.make_episodic_store().export_summary()
            attach_episodic_threads_to_federated(federated, ep_sum_after)

        return self.save() if persist else self.export_payload()

    def reinforce_cluster(
        self,
        node_ids: Sequence[str],
        reason: str = "query_coactivation",
        apply_global_decay: bool = True,
    ) -> int:
        """Hebbian reinforcement: 'neurons that fire together wire together'."""
        present = [nid for nid in dict.fromkeys(node_ids) if nid in self.nodes]
        if len(present) < 2:
            return 0
        if apply_global_decay:
            self.apply_decay()

        now_iso = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        for nid in present:
            self.access_counts[nid] += 1
            self.last_activated[nid] = now_iso

        updated_pairs = 0
        for i in range(len(present)):
            for j in range(i + 1, len(present)):
                u, v = present[i], present[j]
                sim = (
                    _dot(self.vectors[u], self.vectors[v])
                    if u in self.vectors and v in self.vectors
                    else 0.0
                )
                cur = self.synapses[u].get(v)
                prev_w = cur["weight"] if cur else 0.08
                prev_c = cur["coactivations"] if cur else 0
                new_w = round(min(1.0, prev_w + self.learning_rate), 4)
                rec = {
                    "weight": new_w,
                    "coactivations": prev_c + 1,
                    "similarity": round(sim, 4),
                    "origin": "hebbian_coactivation",
                }
                self.synapses[u][v] = dict(rec)
                self.synapses[v][u] = dict(rec)
                updated_pairs += 1

        self.coactivation_events.append(
            {
                "timestamp": now_iso,
                "reason": reason,
                "nodes": present,
                "pairs_reinforced": updated_pairs,
            }
        )
        self.coactivation_events = self.coactivation_events[-50:]
        self.save()
        return updated_pairs

    def apply_decay(self, prune_below: float = 0.04) -> None:
        to_prune: list[tuple[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for u, nbrs in self.synapses.items():
            for v, rec in nbrs.items():
                pair = (min(u, v), max(u, v))
                if pair in seen:
                    continue
                seen.add(pair)
                w = round(rec["weight"] * self.decay_rate, 4)
                if w < prune_below:
                    to_prune.append(pair)
                else:
                    self.synapses[u][v]["weight"] = w
                    self.synapses[v][u]["weight"] = w
        for u, v in to_prune:
            self.synapses[u].pop(v, None)
            self.synapses[v].pop(u, None)

    def resolve_node_id(self, candidate: str) -> str | None:
        """Resolve an exact or case-insensitive node ID or script path (e.g. 'WP-002' or 'src/a.py')."""
        cand = candidate.strip()
        if not cand:
            return None
        if cand in self.nodes:
            return cand
        if f"SCR:{cand}" in self.nodes:
            return f"SCR:{cand}"
        upper = cand.upper()
        if upper in self.nodes:
            return upper
        return None

    def query(
        self,
        query_text: str,
        *,
        top_k: int = 6,
        max_flipped: int = 4,
        reinforce: bool = True,
        ref_date: date | None = None,
    ) -> dict[str, Any]:
        """Dual-Path Retrieval: Base Semantic/Keyword Top-k + Spreading Activation Flip Top-m."""
        if not self.nodes:
            return {"query": query_text, "results": [], "hubs": []}

        ref_date = ref_date or date.today()
        anchor_nid = self.resolve_node_id(query_text)
        if anchor_nid and anchor_nid in self.vectors:
            q_vec = self.vectors[anchor_nid]
            q_kws = set(self.nodes[anchor_nid].get("keywords", []))
        else:
            q_vec = self.embedder.embed_many(
                [query_text], is_query=True, persist_cache=reinforce
            )[0]
            q_kws = _extract_keywords(query_text)

        base_scores: dict[str, float] = {}
        sem_scores: dict[str, float] = {}
        kw_scores: dict[str, float] = {}

        for nid, node in self.nodes.items():
            vec = self.vectors.get(nid)
            raw_sim = _dot(q_vec, vec) if vec else 0.0
            norm_sim = max(0.0, (raw_sim + 1.0) / 2.0) if self.embedder.active_backend in DENSE_BACKENDS else max(0.0, raw_sim)
            sem_scores[nid] = round(raw_sim, 4)

            node_kws = set(node.get("keywords", []))
            kw_overlap = (
                len(q_kws & node_kws) / max(1, len(q_kws)) if q_kws and node_kws else 0.0
            )
            kw_scores[nid] = round(kw_overlap, 4)
            recency = _compute_recency(node.get("updated"), ref_date)
            base_scores[nid] = (norm_sim + 0.30 * kw_overlap) * recency

        # Spreading Activation across Hebbian synapses
        spread_scores = dict(base_scores)
        spread_traces: dict[str, list[dict[str, Any]]] = defaultdict(list)

        for src_id, s_base in base_scores.items():
            if s_base < self.spreading_threshold:
                continue
            for dst_id, syn in self.synapses.get(src_id, {}).items():
                w = syn["weight"]
                boost = self.spreading_beta * s_base * w
                spread_scores[dst_id] += boost
                spread_traces[dst_id].append(
                    {
                        "via": src_id,
                        "synapse_weight": round(w, 3),
                        "boost": round(boost, 4),
                    }
                )

        candidate_ids = [nid for nid in self.nodes if nid != anchor_nid]
        base_ranked = sorted(candidate_ids, key=lambda nid: (-base_scores[nid], nid))
        spread_ranked = sorted(candidate_ids, key=lambda nid: (-spread_scores[nid], nid))

        base_selected = base_ranked[:top_k]
        base_set = set(base_selected)

        flipped_selected: list[str] = []
        for nid in spread_ranked[: top_k + max_flipped * 2]:
            if nid not in base_set and spread_traces.get(nid):
                flipped_selected.append(nid)
                if len(flipped_selected) >= max_flipped:
                    break

        results: list[dict[str, Any]] = []
        for nid in base_selected:
            node = self.nodes[nid]
            results.append(
                {
                    "id": nid,
                    "graph": node["graph"],
                    "title": node["title"],
                    "status": node["status"],
                    "path": "base",
                    "flipped": False,
                    "semantic_similarity": sem_scores[nid],
                    "keyword_overlap": kw_scores[nid],
                    "base_score": round(base_scores[nid], 4),
                    "final_score": round(spread_scores[nid], 4),
                    "spread_sources": sorted(
                        spread_traces.get(nid, []), key=lambda x: -x["boost"]
                    )[:3],
                }
            )
        for nid in flipped_selected:
            node = self.nodes[nid]
            results.append(
                {
                    "id": nid,
                    "graph": node["graph"],
                    "title": node["title"],
                    "status": node["status"],
                    "path": "hebbian_flip",
                    "flipped": True,
                    "semantic_similarity": sem_scores[nid],
                    "keyword_overlap": kw_scores[nid],
                    "base_score": round(base_scores[nid], 4),
                    "final_score": round(spread_scores[nid], 4),
                    "spread_sources": sorted(
                        spread_traces.get(nid, []), key=lambda x: -x["boost"]
                    )[:3],
                }
            )

        reinforced = 0
        if reinforce and len(results) >= 2:
            cluster_ids = [r["id"] for r in results[: min(8, len(results))]]
            if anchor_nid:
                cluster_ids = [anchor_nid, *cluster_ids[:7]]
            reinforced = self.reinforce_cluster(
                cluster_ids,
                reason=f"query:{query_text[:60]}",
            )

        out_payload: dict[str, Any] = {
            "query": query_text,
            "resolved_anchor_node": anchor_nid,
            "embedding_backend": self.embedder.active_backend,
            "embedding_model": self.embedder.effective_model_id,
            "base_count": len(base_selected),
            "flipped_count": len(flipped_selected),
            "pairs_reinforced": reinforced,
            "results": results,
            "hubs": self.detect_hubs()[:6],
        }
        return out_payload

    def related(
        self,
        federated: Mapping[str, Any],
        *,
        node_id: str | None = None,
        draft_file: Path | None = None,
        draft_text: str | None = None,
        per_graph: int = 4,
        novel_top_k: int = 8,
        reinforce: bool = False,
    ) -> dict[str, Any]:
        """Agent-facing cross-graph relevance & neighborhood inspector.

        Supports inspecting:
        1. An existing node ID (`WP-002`, `INT-003`, `KD-001`, `src/workbench_api.py`), reusing its
           full rich embedding vector and contrasting `declared` links vs. `novel_discovery` matches;
        2. An uncommitted draft file (`--draft-file /path/to/draft_WP.md`), encoding it in symmetric
           document space without mutating any graph or cache;
        3. Free draft text (`--text "..."`), ranking candidate intents, plans, KDs, and scripts.
        """
        if not self.nodes:
            return {"error": "empty_graph", "by_graph": {}}

        declared_by_target: dict[str, list[str]] = defaultdict(list)
        anchor_info: dict[str, Any]
        anchor_nid: str | None = None

        if node_id:
            resolved = self.resolve_node_id(node_id)
            if not resolved:
                raise ValueError(
                    f"Unknown node ID {node_id!r}. Available examples: "
                    + ", ".join(sorted(self.nodes)[:8])
                )
            anchor_nid = resolved
            anode = self.nodes[anchor_nid]
            anchor_vec = self.vectors[anchor_nid]
            anchor_kws = set(anode.get("keywords", []))
            anchor_info = {
                "mode": "node",
                "id": anchor_nid,
                "graph": anode["graph"],
                "title": anode["title"],
                "status": anode["status"],
            }
            # Collect all explicit/observed links touching `anchor_nid`
            all_edges = [
                *federated.get("intent", {}).get("edges", []),
                *federated.get("specs", {}).get("edges", []),
                *federated.get("plan", {}).get("edges", []),
                *federated.get("knowledge_debt", {}).get("edges", []),
                *federated.get("scripts", {}).get("edges", []),
                *federated.get("cross_edges", []),
            ]
            for e in all_edges:
                u, v, rel = e.get("from"), e.get("to"), e.get("relationship", "linked")
                if u == anchor_nid and v and v != anchor_nid:
                    tag = f"{rel} (->)"
                    if tag not in declared_by_target[v]:
                        declared_by_target[v].append(tag)
                elif v == anchor_nid and u and u != anchor_nid:
                    tag = f"{rel} (<-)"
                    if tag not in declared_by_target[u]:
                        declared_by_target[u].append(tag)
        elif draft_file is not None:
            raw_content = draft_file.read_text(encoding="utf-8", errors="replace").strip()
            if not raw_content:
                raise ValueError(f"Draft file is empty: {draft_file}")
            compact = re.sub(r"\s+", " ", raw_content)[:3200]
            desc = f"[Draft {draft_file.name}] {compact}"
            anchor_vec = self.embedder.embed_many(
                [desc], is_query=False, persist_cache=False
            )[0]
            anchor_kws = _extract_keywords(compact)
            anchor_info = {
                "mode": "draft_file",
                "path": str(draft_file),
                "preview": compact[:140],
            }
        elif draft_text and draft_text.strip():
            clean_txt = draft_text.strip()
            anchor_vec = self.embedder.embed_many(
                [clean_txt], is_query=True, persist_cache=False
            )[0]
            anchor_kws = _extract_keywords(clean_txt)
            anchor_info = {
                "mode": "draft_text",
                "text": clean_txt[:200],
            }
        else:
            raise ValueError("Provide one of node_id, draft_file, or draft_text.")

        # Score every node across all 4 graphs (no Top-4 static truncation!)
        scored_items: list[dict[str, Any]] = []
        direct_syns = self.synapses.get(anchor_nid, {}) if anchor_nid else {}

        # First pass: compute raw cosine + keyword overlap so we can also compute 1-hop spreading for drafts
        raw_sims: dict[str, float] = {}
        base_vals: dict[str, float] = {}
        kw_vals: dict[str, float] = {}
        for nid, node in self.nodes.items():
            if nid == anchor_nid:
                continue
            vec = self.vectors.get(nid)
            sim = _dot(anchor_vec, vec) if vec else 0.0
            raw_sims[nid] = sim
            norm_sim = (
                max(0.0, (sim + 1.0) / 2.0)
                if self.embedder.active_backend in DENSE_BACKENDS
                else max(0.0, sim)
            )
            nkws = set(node.get("keywords", []))
            kw_ov = (
                len(anchor_kws & nkws) / max(1, len(anchor_kws))
                if anchor_kws and nkws
                else 0.0
            )
            kw_vals[nid] = kw_ov
            base_vals[nid] = norm_sim + 0.25 * kw_ov

        # 1-hop spreading activation (from anchor if node mode, else only from top-4 base seeds so hubs don't drown specific leaves)
        spread_boosts: dict[str, float] = defaultdict(float)
        spread_via: dict[str, str] = {}
        if anchor_nid:
            for dst_id, syn in direct_syns.items():
                if dst_id != anchor_nid:
                    b = self.spreading_beta * syn["weight"]
                    spread_boosts[dst_id] = min(0.25, spread_boosts[dst_id] + b)
                    spread_via[dst_id] = anchor_nid
        else:
            top_seeds = sorted(
                base_vals.items(), key=lambda kv: (-kv[1], kv[0])
            )[:4]
            best_edge_boost: dict[str, float] = defaultdict(float)
            for src_id, bscore in top_seeds:
                if bscore < self.spreading_threshold:
                    continue
                for dst_id, syn in self.synapses.get(src_id, {}).items():
                    b = 0.16 * bscore * syn["weight"]
                    if b > best_edge_boost[dst_id]:
                        best_edge_boost[dst_id] = b
                        spread_via[dst_id] = src_id
                    spread_boosts[dst_id] = min(0.22, spread_boosts[dst_id] + b)

        for nid, node in self.nodes.items():
            if nid == anchor_nid:
                continue
            syn_rec = direct_syns.get(nid)
            syn_w = round(float(syn_rec["weight"]), 4) if syn_rec else 0.0
            syn_co = int(syn_rec["coactivations"]) if syn_rec else 0
            decl_rels = declared_by_target.get(nid, [])
            combined = round(base_vals[nid] + spread_boosts[nid] + 0.18 * syn_w, 4)
            entry: dict[str, Any] = {
                "id": nid,
                "graph": node["graph"],
                "title": node["title"],
                "status": node["status"],
                "relation_status": "declared" if decl_rels else "novel_discovery",
                "declared_relations": decl_rels,
                "semantic_similarity": round(raw_sims[nid], 4),
                "keyword_overlap": round(kw_vals[nid], 4),
                "synapse_weight": syn_w,
                "coactivations": syn_co,
                "combined_score": combined,
            }
            if nid in spread_via and spread_via[nid] != anchor_nid:
                entry["spread_via"] = spread_via[nid]
            scored_items.append(entry)

        scored_items.sort(key=lambda x: (-x["combined_score"], -x["semantic_similarity"], x["id"]))

        by_graph: dict[str, list[dict[str, Any]]] = {
            "intent": [],
            "specs": [],
            "plan": [],
            "knowledge_debt": [],
            "scripts": [],
        }
        for item in scored_items:
            g = item["graph"]
            if g in by_graph and len(by_graph[g]) < per_graph:
                by_graph[g].append(item)

        novel_top = [
            item for item in scored_items if item["relation_status"] == "novel_discovery"
        ][:novel_top_k]

        declared_summary = [
            {
                "id": tid,
                "graph": self.nodes[tid]["graph"] if tid in self.nodes else "external",
                "title": self.nodes[tid]["title"] if tid in self.nodes else tid,
                "relations": rels,
                "semantic_similarity": round(raw_sims.get(tid, 0.0), 4),
            }
            for tid, rels in sorted(declared_by_target.items())
        ]

        reinforced = 0
        if reinforce and scored_items:
            top_ids = [x["id"] for x in scored_items[:6]]
            if anchor_nid:
                top_ids = [anchor_nid, *top_ids]
            reinforced = self.reinforce_cluster(top_ids, reason=f"related:{anchor_nid or 'draft'}")

        # Surface matching `EVAL-###` substantive evaluations linked to anchor or top hits
        top_hit_ids = {anchor_nid} if anchor_nid else set()
        top_hit_ids.update(x["id"] for x in scored_items[:8])
        related_evals: list[dict[str, Any]] = []
        for ev in federated.get("evaluations", {}).get("nodes", []):
            ev_targets = set(
                [
                    *ev.get("evaluates_intents", []),
                    *ev.get("evaluates_specs", []),
                    *ev.get("evaluates_plans", []),
                    *(f"SCR:{s}" for s in ev.get("evaluates_scripts", [])),
                ]
            )
            ev_kws = _extract_keywords(
                f"{ev['title']} {ev['perspective']} {ev['summary']} "
                + " ".join(ev.get("preserved_qualities", []))
                + " "
                + " ".join(ev.get("at_risk_qualities", []))
            )
            kw_hit = len(anchor_kws & ev_kws) / max(1, len(anchor_kws)) if anchor_kws else 0.0
            direct_hit = bool(anchor_nid and anchor_nid in ev_targets)
            neighbor_overlap = sorted(ev_targets & top_hit_ids)
            if direct_hit or neighbor_overlap or kw_hit > 0.08:
                score = (1.0 if direct_hit else 0.0) + 0.25 * len(neighbor_overlap) + kw_hit
                related_evals.append(
                    {
                        "id": ev["id"],
                        "title": ev["title"],
                        "kind": ev["kind"],
                        "verdict": ev["verdict"],
                        "perspective": ev["perspective"],
                        "summary": ev["summary"],
                        "matched_targets": neighbor_overlap,
                        "relevance_score": round(score, 4),
                    }
                )
        related_evals.sort(key=lambda e: (-e["relevance_score"], e["id"]))

        # Surface matching `THR-###` disentangled episodic threads
        related_threads: list[dict[str, Any]] = []
        for th in federated.get("episodic_memory", {}).get("threads", []):
            th_nodes = {lnk["node_id"] for lnk in th.get("linked_nodes", [])}
            th_kws = _extract_keywords(
                th["title"]
                + " "
                + (th.get("capsule_summary") or "")
                + " "
                + " ".join(s.get("user_slice", "") for s in th.get("spans", []))
            )
            kw_hit = len(anchor_kws & th_kws) / max(1, len(anchor_kws)) if anchor_kws else 0.0
            direct_hit = bool(anchor_nid and anchor_nid in th_nodes)
            overlap_nodes = sorted(th_nodes & top_hit_ids)
            if direct_hit or overlap_nodes or kw_hit > 0.08:
                t_score = (1.0 if direct_hit else 0.0) + 0.25 * len(overlap_nodes) + kw_hit
                related_threads.append(
                    {
                        "id": th["id"],
                        "title": th["title"],
                        "status": th["status"],
                        "span_count": th["span_count"],
                        "capsule_summary": th.get("capsule_summary"),
                        "matched_nodes": overlap_nodes,
                        "relevance_score": round(t_score, 4),
                    }
                )
        related_threads.sort(key=lambda t: (-t["relevance_score"], t["id"]))

        return {
            "anchor": anchor_info,
            "embedding_backend": self.embedder.active_backend,
            "embedding_model": self.embedder.effective_model_id,
            "pairs_reinforced": reinforced,
            "declared_links": declared_summary,
            "novel_discoveries": novel_top,
            "related_evaluations": related_evals[:5],
            "related_threads": related_threads[:5],
            "by_graph": by_graph,
        }

    def detect_hubs(self) -> list[dict[str, Any]]:
        """Identify high-connectivity associative hubs across all four graphs."""
        hubs: list[dict[str, Any]] = []
        for nid in sorted(self.nodes):
            nbrs = self.synapses.get(nid, {})
            total_w = round(sum(rec["weight"] for rec in nbrs.values()), 4)
            deg = len(nbrs)
            is_hub = total_w >= self.hub_threshold or deg >= 4
            hubs.append(
                {
                    "id": nid,
                    "graph": self.nodes[nid]["graph"],
                    "title": self.nodes[nid]["title"],
                    "degree": deg,
                    "associative_strength": total_w,
                    "access_count": self.access_counts.get(nid, 0),
                    "is_hub": is_hub,
                }
            )
        hubs.sort(key=lambda h: (-h["associative_strength"], -h["degree"], h["id"]))
        return hubs

    def export_payload(self) -> dict[str, Any]:
        synapse_list: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for u in sorted(self.synapses):
            for v in sorted(self.synapses[u]):
                pair = (min(u, v), max(u, v))
                if pair in seen:
                    continue
                seen.add(pair)
                rec = self.synapses[u][v]
                synapse_list.append(
                    {
                        "from": pair[0],
                        "to": pair[1],
                        "weight": rec["weight"],
                        "coactivations": rec["coactivations"],
                        "similarity": rec.get("similarity", 0.0),
                        "origin": rec.get("origin", "semantic_seed"),
                        "provenance": "associative",
                    }
                )
        synapse_list.sort(key=lambda e: (-e["weight"], e["from"], e["to"]))
        hubs = self.detect_hubs()
        return {
            "schema_version": HEBBIAN_SCHEMA,
            "embedding_backend": self.embedder.active_backend,
            "embedding_model": self.embedder.effective_model_id,
            "node_count": len(self.nodes),
            "synapse_count": len(synapse_list),
            "hubs": [h for h in hubs if h["is_hub"]],
            "all_node_strengths": hubs,
            "access_counts": dict(sorted(self.access_counts.items())),
            "last_activated": dict(sorted(self.last_activated.items())),
            "coactivation_events": self.coactivation_events,
            "synapses": synapse_list,
        }

    def save(self) -> dict[str, Any]:
        payload = self.export_payload()
        self.assoc_path.parent.mkdir(parents=True, exist_ok=True)
        self.assoc_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        return payload
