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
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

SKILL_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MLX_MODEL = "mlx-community/Qwen3-Embedding-0.6B-4bit-DWQ"
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


def _detect_mlx_python() -> str | None:
    """Return path to Python interpreter with `mlx_embeddings`, checking current & `.venv`."""
    try:
        import mlx_embeddings  # noqa: F401
        return sys.executable
    except ImportError:
        pass
    venv_py = SKILL_ROOT / ".venv" / "bin" / "python"
    if venv_py.is_file():
        res = subprocess.run(
            [str(venv_py), "-c", "import mlx_embeddings"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if res.returncode == 0:
            return str(venv_py)
    return None


class TieredEmbedder:
    """Content-addressed local embedder supporting MLX (`Qwen3-Embedding-0.6B-4bit`) & fallback."""

    def __init__(
        self,
        cache_path: Path,
        backend: str = "auto",
        model_id: str = DEFAULT_MLX_MODEL,
    ) -> None:
        self.cache_path = cache_path
        self.requested_backend = backend
        self.model_id = model_id
        self.active_backend, self.mlx_python = self._resolve_backend(backend)
        self.effective_model_id = (
            model_id if self.active_backend == "mlx" else "ptm-stdlib-ngram-384"
        )
        self._cache: dict[str, list[float]] = {}
        self._dirty = False
        self._load_cache()

    def _resolve_backend(self, backend: str) -> tuple[str, str | None]:
        if backend == "hash":
            return "hash", None
        mlx_py = _detect_mlx_python()
        if backend == "mlx":
            if not mlx_py:
                raise RuntimeError(
                    "MLX backend requested, but mlx-embeddings is not installed."
                )
            return "mlx", mlx_py
        if mlx_py:
            return "mlx", mlx_py
        return "hash", None

    def _load_cache(self) -> None:
        if self.cache_path.is_file():
            try:
                raw = json.loads(self.cache_path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    self._cache = raw.get("vectors", {})
            except (OSError, json.JSONDecodeError):
                self._cache = {}

    def save_cache(self) -> None:
        if not self._dirty:
            return
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "backend": self.active_backend,
            "model_id": self.effective_model_id,
            "count": len(self._cache),
            "vectors": self._cache,
        }
        self.cache_path.write_text(
            json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        self._dirty = False

    def _key(self, text: str) -> str:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:24]
        return f"{self.effective_model_id}:{digest}"

    def embed_many(self, texts: Sequence[str], *, is_query: bool = False) -> list[list[float]]:
        formatted = [
            (QUERY_INSTRUCTION + t if (is_query and self.active_backend == "mlx") else t)
            for t in texts
        ]
        keys = [self._key(t) for t in formatted]
        missing_indices = [i for i, k in enumerate(keys) if k not in self._cache]

        if missing_indices:
            missing_texts = [formatted[i] for i in missing_indices]
            if self.active_backend == "mlx":
                if self.mlx_python == sys.executable:
                    computed = _embed_with_mlx_inproc(missing_texts, self.model_id)
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
                        input=json.dumps({"texts": missing_texts, "model": self.model_id}),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        check=True,
                    )
                    computed = json.loads(proc.stdout)
            else:
                computed = [_stdlib_hash_embed(t) for t in missing_texts]

            for idx, vec in zip(missing_indices, computed):
                self._cache[keys[idx]] = vec
            self._dirty = True
            self.save_cache()

        return [self._cache[k] for k in keys]


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


def _unified_nodes_from_federated(federated: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Convert all 4 federated graphs into rich textual descriptors for associative indexing."""
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

    for n in federated.get("plan", {}).get("nodes", []):
        ctx = n.get("context") or {}
        text = (
            f"[Plan {n['id']} ({n['level']})] {n['title']}. Objective: {n['objective']} "
            f"Deliverables: {'; '.join(n.get('deliverables', []))}. "
            f"Acceptance: {'; '.join(n.get('acceptance', []))}. "
            f"Approach: {n.get('approach', '')}. Problem: {ctx.get('problem', '')}. "
            f"Qualities: {'; '.join(n.get('qualities', []))}."
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
            self.repo_root / "_aiHumanInteract" / ".cache" / "embeddings.json"
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

    def sync_federated(self, federated: Mapping[str, Any]) -> dict[str, Any]:
        """Embed all current nodes across the 4 graphs and seed/prune associative synapses."""
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
            [self.nodes[nid]["text"] for nid in ordered_ids], is_query=False
        )
        self.vectors = dict(zip(ordered_ids, vecs))

        # Collect structural pairs so we distinguish novel associative bridges from declared links
        declared_pairs: set[tuple[str, str]] = set()
        for gname in ("intent", "plan", "knowledge_debt", "scripts"):
            for e in federated.get(gname, {}).get("edges", []):
                declared_pairs.add((e["from"], e["to"]))
                declared_pairs.add((e["to"], e["from"]))
        for e in federated.get("cross_edges", []):
            declared_pairs.add((e["from"], e["to"]))
            declared_pairs.add((e["to"], e["from"]))

        seed_thresh = 0.44 if self.embedder.active_backend == "mlx" else 0.26

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

        return self.save()

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
        q_vec = self.embedder.embed_many([query_text], is_query=True)[0]
        q_kws = _extract_keywords(query_text)

        base_scores: dict[str, float] = {}
        sem_scores: dict[str, float] = {}
        kw_scores: dict[str, float] = {}

        for nid, node in self.nodes.items():
            vec = self.vectors.get(nid)
            raw_sim = _dot(q_vec, vec) if vec else 0.0
            norm_sim = max(0.0, (raw_sim + 1.0) / 2.0) if self.embedder.active_backend == "mlx" else max(0.0, raw_sim)
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

        base_ranked = sorted(self.nodes, key=lambda nid: (-base_scores[nid], nid))
        spread_ranked = sorted(self.nodes, key=lambda nid: (-spread_scores[nid], nid))

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
            reinforced = self.reinforce_cluster(
                [r["id"] for r in results[: min(8, len(results))]],
                reason=f"query:{query_text[:60]}",
            )

        return {
            "query": query_text,
            "embedding_backend": self.embedder.active_backend,
            "embedding_model": self.embedder.effective_model_id,
            "base_count": len(base_selected),
            "flipped_count": len(flipped_selected),
            "pairs_reinforced": reinforced,
            "results": results,
            "hubs": self.detect_hubs()[:6],
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
