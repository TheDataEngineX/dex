"""CareerDEX Phase 3: Feature Engineering & Embeddings (Issue #67).

Implements text parsing, skill extraction, embedding generation, and
vector-store integration for semantic job matching.

Components:
    - ``JobDescriptionParser`` — extracts skills, salary, seniority from text
    - ``ResumeParser`` — extracts structured fields from resume text
    - ``SkillNormalizer`` — maps skill aliases to a canonical taxonomy
    - ``EmbeddingGenerator`` — ``sentence-transformers`` wrapper (CPU-safe)
    - ``VectorStore`` — abstract interface backed by ChromaDB or in-memory
"""

from __future__ import annotations

import abc
import math
import re
from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from careerdex.core.exceptions import MissingDependencyError

__all__ = [
    "EmbeddingGenerator",
    "InMemoryVectorStore",
    "JobDescriptionParser",
    "ResumeParser",
    "SkillNormalizer",
    "VectorStore",
]


# ======================================================================
# Job description parsing
# ======================================================================

_SALARY_PATTERN = re.compile(
    r"\$\s*([\d,]+(?:\.\d+)?)\s*(?:[-–—to]+\s*\$?\s*([\d,]+(?:\.\d+)?))?",
    re.IGNORECASE,
)

_SENIORITY_KEYWORDS: dict[str, list[str]] = {
    "entry_level": ["entry level", "junior", "associate", "intern", "graduate", "new grad"],
    "mid_level": ["mid level", "mid-level", "intermediate"],
    "senior": ["senior", "sr.", "lead", "staff", "principal"],
    "executive": ["executive", "director", "vp", "vice president", "c-level", "cto", "ceo"],
}


@dataclass
class ParsedJobDescription:
    """Structured output from job description parsing."""

    title_normalised: str = ""
    skills: list[str] = field(default_factory=list)
    seniority: str = "unknown"
    salary_min: float | None = None
    salary_max: float | None = None
    remote: bool = False
    location_city: str = ""
    location_country: str = ""


class JobDescriptionParser:
    """Extract structured fields from raw job description text."""

    def parse(self, title: str, description: str) -> ParsedJobDescription:
        """Parse a job description into structured fields.

        Args:
            title: Job title string.
            description: Full job description text.

        Returns:
            ``ParsedJobDescription`` with extracted fields.
        """
        combined = f"{title} {description}".lower()

        return ParsedJobDescription(
            title_normalised=self._normalise_title(title),
            skills=self._extract_skills(combined),
            seniority=self._detect_seniority(combined),
            salary_min=self._extract_salary(description)[0],
            salary_max=self._extract_salary(description)[1],
            remote="remote" in combined or "work from home" in combined,
        )

    @staticmethod
    def _normalise_title(title: str) -> str:
        """Lower-case, strip extra whitespace."""
        return " ".join(title.strip().lower().split())

    @staticmethod
    def _extract_skills(text: str) -> list[str]:
        """Regex-based skill extraction from text."""
        # Canonical list of tech skills to look for
        known_skills = [
            "python",
            "java",
            "javascript",
            "typescript",
            "go",
            "rust",
            "c++",
            "sql",
            "nosql",
            "mongodb",
            "postgresql",
            "mysql",
            "redis",
            "aws",
            "gcp",
            "azure",
            "docker",
            "kubernetes",
            "terraform",
            "spark",
            "kafka",
            "airflow",
            "dbt",
            "snowflake",
            "databricks",
            "react",
            "node.js",
            "fastapi",
            "flask",
            "django",
            "machine learning",
            "deep learning",
            "nlp",
            "computer vision",
            "pytorch",
            "tensorflow",
            "scikit-learn",
            "pandas",
            "numpy",
            "git",
            "ci/cd",
            "linux",
            "agile",
            "scrum",
        ]
        found: list[str] = []
        for skill in known_skills:
            pattern = r"\b" + re.escape(skill) + r"\b"
            if re.search(pattern, text, re.IGNORECASE):
                found.append(skill)
        return sorted(set(found))

    @staticmethod
    def _detect_seniority(text: str) -> str:
        for level, keywords in _SENIORITY_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    return level
        return "unknown"

    @staticmethod
    def _extract_salary(text: str) -> tuple[float | None, float | None]:
        match = _SALARY_PATTERN.search(text)
        if not match:
            return None, None
        raw_min = match.group(1).replace(",", "")
        sal_min = float(raw_min)
        sal_max = None
        if match.group(2):
            sal_max = float(match.group(2).replace(",", ""))
        return sal_min, sal_max


# ======================================================================
# Resume parsing
# ======================================================================


@dataclass
class ParsedResume:
    """Structured output from resume parsing."""

    name: str = ""
    email: str = ""
    phone: str = ""
    skills: list[str] = field(default_factory=list)
    experience_years: int = 0
    education: str = ""
    current_title: str = ""


class ResumeParser:
    """Extract structured fields from resume text.

    In production, PDF-to-text is handled by ``pdfplumber`` and
    DOCX by ``python-docx``.  This class operates on plain text.
    """

    _EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
    _PHONE_RE = re.compile(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}")

    def parse(self, text: str) -> ParsedResume:
        """Parse resume plain-text into structured fields."""
        email_match = self._EMAIL_RE.search(text)
        phone_match = self._PHONE_RE.search(text)
        skills = JobDescriptionParser._extract_skills(text.lower())

        return ParsedResume(
            email=email_match.group(0) if email_match else "",
            phone=phone_match.group(0) if phone_match else "",
            skills=skills,
        )


# ======================================================================
# Skill normalisation
# ======================================================================

_SKILL_ALIASES: dict[str, str] = {
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "k8s": "kubernetes",
    "tf": "terraform",
    "ml": "machine learning",
    "dl": "deep learning",
    "react.js": "react",
    "reactjs": "react",
    "node": "node.js",
    "nodejs": "node.js",
    "postgres": "postgresql",
    "mongo": "mongodb",
    "scikit learn": "scikit-learn",
    "sklearn": "scikit-learn",
}

_SKILL_CATEGORIES: dict[str, str] = {
    "python": "language",
    "java": "language",
    "javascript": "language",
    "typescript": "language",
    "go": "language",
    "rust": "language",
    "c++": "language",
    "sql": "language",
    "react": "framework",
    "node.js": "framework",
    "fastapi": "framework",
    "flask": "framework",
    "django": "framework",
    "pytorch": "framework",
    "tensorflow": "framework",
    "scikit-learn": "framework",
    "docker": "tool",
    "kubernetes": "tool",
    "terraform": "tool",
    "git": "tool",
    "spark": "tool",
    "kafka": "tool",
    "airflow": "tool",
    "dbt": "tool",
    "aws": "platform",
    "gcp": "platform",
    "azure": "platform",
    "snowflake": "platform",
    "databricks": "platform",
    "machine learning": "domain",
    "deep learning": "domain",
    "nlp": "domain",
    "computer vision": "domain",
}


class SkillNormalizer:
    """Maps skill aliases to canonical names and categorises them."""

    def __init__(
        self,
        aliases: dict[str, str] | None = None,
        categories: dict[str, str] | None = None,
    ) -> None:
        self.aliases = aliases or dict(_SKILL_ALIASES)
        self.categories = categories or dict(_SKILL_CATEGORIES)

    def normalize(self, skill: str) -> str:
        """Return canonical name for *skill*."""
        key = skill.strip().lower()
        return self.aliases.get(key, key)

    def categorize(self, skill: str) -> str:
        """Return the category of *skill* or ``'other'``."""
        canonical = self.normalize(skill)
        return self.categories.get(canonical, "other")

    def normalize_list(self, skills: list[str]) -> list[str]:
        """Normalise and deduplicate a list of skills."""
        seen: set[str] = set()
        result: list[str] = []
        for s in skills:
            n = self.normalize(s)
            if n not in seen:
                seen.add(n)
                result.append(n)
        return result


# ======================================================================
# Embedding generation
# ======================================================================


class EmbeddingGenerator:
    """Generate text embeddings via *sentence-transformers* (optional dep).

    Raises ``MissingDependencyError`` at embedding time if the library
    is not installed — there is NO silent fallback.  Install with::

        pip install sentence-transformers

    The ``_hash_embed`` method exists only for **explicit testing** use
    (call it directly if you need deterministic test vectors).
    """

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        dimension: int = 384,
    ) -> None:
        self.model_name = model_name
        self.dimension = dimension
        self._model: Any = None

        try:
            from sentence_transformers import SentenceTransformer  # type: ignore[import-untyped]

            self._model = SentenceTransformer(model_name)
            self.dimension = self._model.get_sentence_embedding_dimension()
            logger.info("loaded sentence-transformers model=%s dim=%d", model_name, self.dimension)
        except ImportError:
            logger.warning(
                "sentence-transformers not installed — embed()/embed_batch() "
                "will raise MissingDependencyError until installed",
            )

    def embed(self, text: str) -> list[float]:
        """Generate an embedding vector for *text*.

        Raises:
            MissingDependencyError: If ``sentence-transformers`` is not installed.
        """
        if self._model is not None:
            vec = self._model.encode(text)
            return vec.tolist()
        msg = (
            "sentence-transformers is required for embedding generation. "
            "Install it with: pip install sentence-transformers"
        )
        raise MissingDependencyError(msg)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of texts.

        Raises:
            MissingDependencyError: If ``sentence-transformers`` is not installed.
        """
        if self._model is not None:
            vecs = self._model.encode(texts)
            return [v.tolist() for v in vecs]
        msg = (
            "sentence-transformers is required for batch embedding generation. "
            "Install it with: pip install sentence-transformers"
        )
        raise MissingDependencyError(msg)

    def _hash_embed(self, text: str) -> list[float]:
        """Deterministic hash-based embedding (TESTING ONLY).

        This method does NOT produce semantically meaningful vectors.
        Call it directly in tests when you need a deterministic vector
        without installing ``sentence-transformers``.
        """
        import hashlib

        h = hashlib.sha256(text.encode()).hexdigest()
        vec = [int(h[i : i + 2], 16) / 255.0 for i in range(0, min(len(h), self.dimension * 2), 2)]
        # Pad or truncate to dimension
        vec = (vec + [0.0] * self.dimension)[: self.dimension]
        # L2-normalise
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]


# ======================================================================
# Vector store
# ======================================================================


class VectorStore(abc.ABC):
    """Abstract vector storage interface."""

    @abc.abstractmethod
    def add(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        metadata: list[dict[str, Any]] | None = None,
    ) -> int:
        """Insert vectors. Returns count inserted."""

    @abc.abstractmethod
    def query(
        self,
        embedding: list[float],
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """Return top-k nearest neighbours."""

    @abc.abstractmethod
    def delete(self, ids: list[str]) -> int:
        """Delete vectors by ID. Returns count deleted."""

    @abc.abstractmethod
    def count(self) -> int:
        """Total number of stored vectors."""


class InMemoryVectorStore(VectorStore):
    """In-memory brute-force vector store (testing & small datasets)."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[list[float], dict[str, Any]]] = {}

    def add(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        metadata: list[dict[str, Any]] | None = None,
    ) -> int:
        meta = metadata or [{} for _ in ids]
        for vid, vec, m in zip(ids, embeddings, meta, strict=True):
            self._store[vid] = (vec, m)
        logger.info("vector store: added {} vectors, total={}", len(ids), len(self._store))
        return len(ids)

    def query(self, embedding: list[float], top_k: int = 10) -> list[dict[str, Any]]:
        scored: list[tuple[str, float, dict[str, Any]]] = []
        for vid, (vec, meta) in self._store.items():
            sim = self._cosine(embedding, vec)
            scored.append((vid, sim, meta))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [{"id": vid, "score": round(sim, 4), **meta} for vid, sim, meta in scored[:top_k]]

    def delete(self, ids: list[str]) -> int:
        removed = 0
        for vid in ids:
            if vid in self._store:
                del self._store[vid]
                removed += 1
        return removed

    def count(self) -> int:
        return len(self._store)

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b, strict=False))
        ma = math.sqrt(sum(x * x for x in a)) or 1.0
        mb = math.sqrt(sum(y * y for y in b)) or 1.0
        return dot / (ma * mb)
