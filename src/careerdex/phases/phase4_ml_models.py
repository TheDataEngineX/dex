"""CareerDEX Phase 4: ML Models Training (Issue #68).

Five ML model interfaces for the CareerDEX intelligence platform:

1. **ResumeJobMatcher** — cosine similarity + weighted scoring
2. **SalaryPredictor** — XGBoost regressor for salary percentiles
3. **SkillGapAnalyzer** — TF-IDF + cosine similarity skill gap analysis
4. **CareerPathRecommender** — graph traversal on career transitions
5. **ChurnPredictor** — logistic regression for churn probability

All models are trained on synthetic data derived from domain reference
tables.  Swap with real training data for production accuracy.
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from loguru import logger

from careerdex.core.exceptions import MissingDependencyError

__all__ = [
    "CareerPathRecommender",
    "ChurnPredictor",
    "MatchResult",
    "ModelMetrics",
    "ResumeJobMatcher",
    "SalaryPredictor",
    "SalaryPrediction",
    "SkillGapAnalyzer",
    "SkillRecommendation",
]


# ======================================================================
# Shared dataclasses
# ======================================================================


@dataclass
class ModelMetrics:
    """Container for model performance metrics."""

    model_name: str
    version: str = "1.0.0"
    accuracy: float | None = None
    precision: float | None = None
    recall: float | None = None
    f1_score: float | None = None
    mae: float | None = None
    rmse: float | None = None
    auc: float | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(tz=UTC))


@dataclass
class MatchResult:
    """Result from resume-job matching."""

    job_id: str
    overall_score: float
    embedding_score: float
    skill_score: float
    location_score: float
    salary_score: float


@dataclass
class SalaryPrediction:
    """Salary prediction output."""

    p25: float
    p50: float
    p75: float
    confidence: float
    top_features: list[str] = field(default_factory=list)


@dataclass
class SkillRecommendation:
    """Single skill recommendation."""

    skill: str
    category: str
    demand_score: float
    salary_impact: float
    learning_time_weeks: int


# ======================================================================
# Model 1: Resume-Job Matcher
# ======================================================================


class ResumeJobMatcher:
    """Embedding-based resume-to-job matching with weighted scoring.

    This is the **only implemented model** in Phase 4.  The scoring
    algorithm uses real cosine similarity, set-overlap, and threshold
    heuristics — no ML training required.

    Scoring weights (configurable via constructor):
        - Embedding similarity: 50 %
        - Skill overlap: 20 %
        - Location match: 15 %
        - Salary fit: 15 %
    """

    def __init__(
        self,
        weights: dict[str, float] | None = None,
    ) -> None:
        self.weights = weights or {
            "embedding": 0.50,
            "skill": 0.20,
            "location": 0.15,
            "salary": 0.15,
        }
        self.model_name = "resume-job-matcher"
        self.version = "1.0.0"

    def match(
        self,
        resume_embedding: list[float],
        job_embedding: list[float],
        resume_skills: list[str],
        job_skills: list[str],
        resume_locations: list[str],
        job_location: str,
        salary_expectation: float | None = None,
        salary_min: float | None = None,
        salary_max: float | None = None,
        job_id: str = "",
    ) -> MatchResult:
        """Compute weighted match score between a resume and a job."""
        emb_score = self._cosine(resume_embedding, job_embedding)
        skill_score = self._skill_overlap(resume_skills, job_skills)
        loc_score = self._location_match(resume_locations, job_location)
        sal_score = self._salary_fit(salary_expectation, salary_min, salary_max)

        w = self.weights
        overall = (
            w["embedding"] * emb_score
            + w["skill"] * skill_score
            + w["location"] * loc_score
            + w["salary"] * sal_score
        )

        return MatchResult(
            job_id=job_id,
            overall_score=round(overall, 4),
            embedding_score=round(emb_score, 4),
            skill_score=round(skill_score, 4),
            location_score=round(loc_score, 4),
            salary_score=round(sal_score, 4),
        )

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        if not a or not b:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b, strict=False))
        ma = math.sqrt(sum(x * x for x in a)) or 1.0
        mb = math.sqrt(sum(y * y for y in b)) or 1.0
        return max(0.0, dot / (ma * mb))

    @staticmethod
    def _skill_overlap(resume: list[str], job: list[str]) -> float:
        if not job:
            return 1.0
        r_set = {s.lower() for s in resume}
        j_set = {s.lower() for s in job}
        return len(r_set & j_set) / len(j_set)

    @staticmethod
    def _location_match(preferred: list[str], job_loc: str) -> float:
        if not preferred:
            # No preference stated — neutral score (neither penalise nor reward)
            return 0.5
        jl = job_loc.lower()
        return 1.0 if any(p.lower() in jl or jl in p.lower() for p in preferred) else 0.0

    @staticmethod
    def _salary_fit(
        expectation: float | None,
        sal_min: float | None,
        sal_max: float | None,
    ) -> float:
        if expectation is None or (sal_min is None and sal_max is None):
            # Incomplete salary data — neutral score
            return 0.5
        low = sal_min or 0.0
        # If only min is given, assume a 30 % band above it
        high = sal_max or low * 1.3
        if low <= expectation <= high:
            return 1.0
        diff = min(abs(expectation - low), abs(expectation - high))
        return max(0.0, 1.0 - diff / max(expectation, 1.0))


# ======================================================================
# Model 2: Salary Predictor
# ======================================================================


class SalaryPredictor:
    """Salary prediction using XGBoost regressors.

    Trains three separate XGBRegressor models for the 25th, 50th, and
    75th salary percentiles using synthetic data derived from domain
    reference tables.  Swap the training data with real market data
    for production accuracy.

    Features:
        - title (one-hot encoded)
        - location (one-hot encoded)
        - seniority (one-hot encoded)
        - skill_count (numeric)
        - years_experience (numeric)
    """

    _BASE_SALARIES: dict[str, float] = {
        "software engineer": 140_000,
        "data engineer": 145_000,
        "ml engineer": 160_000,
        "data scientist": 150_000,
        "backend developer": 135_000,
        "frontend developer": 130_000,
        "devops engineer": 140_000,
        "product manager": 145_000,
        "engineering manager": 185_000,
    }

    _LOCATION_MULTIPLIER: dict[str, float] = {
        "san francisco": 1.15,
        "new york": 1.10,
        "seattle": 1.08,
        "austin": 0.95,
        "denver": 0.93,
        "remote": 1.00,
    }

    _SENIORITY_DELTA: dict[str, float] = {
        "entry_level": -30_000,
        "mid_level": 0,
        "senior": 35_000,
        "executive": 80_000,
    }

    def __init__(self, seed: int = 42) -> None:
        self.model_name = "salary-predictor"
        self.version = "1.0.0"
        self._seed = seed

        try:
            from xgboost import XGBRegressor
        except ImportError as exc:
            msg = "SalaryPredictor requires xgboost. Install: uv sync --group ml"
            raise MissingDependencyError(msg) from exc

        self._titles = sorted(self._BASE_SALARIES.keys())
        self._locations = sorted(self._LOCATION_MULTIPLIER.keys())
        self._seniorities = sorted(self._SENIORITY_DELTA.keys())

        X, y_p25, y_p50, y_p75 = self._generate_training_data()

        self._model_p25 = XGBRegressor(
            n_estimators=50,
            max_depth=4,
            random_state=seed,
            verbosity=0,
        )
        self._model_p50 = XGBRegressor(
            n_estimators=50,
            max_depth=4,
            random_state=seed,
            verbosity=0,
        )
        self._model_p75 = XGBRegressor(
            n_estimators=50,
            max_depth=4,
            random_state=seed,
            verbosity=0,
        )
        self._model_p25.fit(X, y_p25)
        self._model_p50.fit(X, y_p50)
        self._model_p75.fit(X, y_p75)

        logger.info(
            "SalaryPredictor trained on %d synthetic samples",
            len(X),
        )

    def _generate_training_data(
        self,
    ) -> tuple[list[list[float]], list[float], list[float], list[float]]:
        """Generate synthetic training data from reference tables."""
        rng = random.Random(self._seed)
        X: list[list[float]] = []
        y_p25: list[float] = []
        y_p50: list[float] = []
        y_p75: list[float] = []

        for title, base in self._BASE_SALARIES.items():
            for loc, mult in self._LOCATION_MULTIPLIER.items():
                for seniority, delta in self._SENIORITY_DELTA.items():
                    for _ in range(5):
                        skill_count = rng.randint(2, 12)
                        years_exp = rng.randint(0, 20)
                        years_bonus = years_exp * 2_000

                        p50 = (base + delta) * mult + years_bonus
                        noise = rng.gauss(0, p50 * 0.05)
                        p50 = max(30_000, p50 + noise)
                        p25 = p50 * rng.uniform(0.82, 0.90)
                        p75 = p50 * rng.uniform(1.10, 1.20)

                        features = self._encode(
                            title,
                            loc,
                            seniority,
                            skill_count,
                            years_exp,
                        )
                        X.append(features)
                        y_p25.append(p25)
                        y_p50.append(p50)
                        y_p75.append(p75)

        return X, y_p25, y_p50, y_p75

    def _encode(
        self,
        title: str,
        location: str,
        seniority: str,
        skill_count: int,
        years_experience: int,
    ) -> list[float]:
        """One-hot encode categorical features + numeric features."""
        row: list[float] = []
        t = title.lower()
        for t_name in self._titles:
            row.append(1.0 if t == t_name else 0.0)
        loc = location.lower()
        for loc_name in self._locations:
            row.append(1.0 if loc == loc_name else 0.0)
        sen = seniority.lower()
        for sen_name in self._seniorities:
            row.append(1.0 if sen == sen_name else 0.0)
        row.append(float(skill_count))
        row.append(float(years_experience))
        return row

    def predict(
        self,
        title: str,
        location: str = "remote",
        seniority: str = "mid_level",
        skills: list[str] | None = None,
        years_experience: int | None = None,
    ) -> SalaryPrediction:
        """Predict salary range for a given role profile."""
        skill_count = len(skills) if skills else 0
        years_exp = years_experience if years_experience is not None else 3

        features = [self._encode(title, location, seniority, skill_count, years_exp)]
        p25 = float(self._model_p25.predict(features)[0])
        p50 = float(self._model_p50.predict(features)[0])
        p75 = float(self._model_p75.predict(features)[0])

        # Ensure ordering: p25 <= p50 <= p75
        p25, p50, p75 = sorted([p25, p50, p75])

        spread = (p75 - p25) / max(p50, 1.0)
        confidence = max(0.0, min(1.0, 1.0 - spread))

        importances = self._model_p50.feature_importances_
        feature_names = (
            [f"title:{t}" for t in self._titles]
            + [f"location:{loc}" for loc in self._locations]
            + [f"seniority:{s}" for s in self._seniorities]
            + ["skill_count", "years_experience"]
        )
        ranked = sorted(
            zip(feature_names, importances, strict=False),
            key=lambda x: x[1],
            reverse=True,
        )
        top_features = [name for name, _ in ranked[:5]]

        return SalaryPrediction(
            p25=round(p25, 2),
            p50=round(p50, 2),
            p75=round(p75, 2),
            confidence=round(confidence, 4),
            top_features=top_features,
        )


# ======================================================================
# Model 3: Skill Gap Analyzer
# ======================================================================


class SkillGapAnalyzer:
    """Skill gap analysis using TF-IDF and cosine similarity.

    Uses the ``_ROLE_SKILL_MAP`` to build a TF-IDF corpus of role
    skill profiles.  Given a user's current skills and a target role,
    identifies the most impactful missing skills ranked by demand
    score (TF-IDF weight in the target role profile).

    Salary impact is estimated from ``SalaryPredictor._BASE_SALARIES``
    deltas.  Learning time is a heuristic based on skill rarity.
    """

    _ROLE_SKILL_MAP: dict[str, list[str]] = {
        "data engineer": [
            "python",
            "sql",
            "spark",
            "airflow",
            "kafka",
            "docker",
            "kubernetes",
            "aws",
            "terraform",
            "dbt",
        ],
        "ml engineer": [
            "python",
            "pytorch",
            "tensorflow",
            "docker",
            "kubernetes",
            "mlflow",
            "spark",
            "sql",
            "aws",
            "fastapi",
        ],
        "data scientist": [
            "python",
            "sql",
            "pandas",
            "scikit-learn",
            "pytorch",
            "statistics",
            "tableau",
            "spark",
            "r",
        ],
        "backend developer": [
            "python",
            "java",
            "sql",
            "docker",
            "kubernetes",
            "redis",
            "postgresql",
            "fastapi",
            "git",
            "ci/cd",
        ],
        "software engineer": [
            "python",
            "java",
            "javascript",
            "sql",
            "docker",
            "kubernetes",
            "git",
            "ci/cd",
            "aws",
            "redis",
        ],
        "devops engineer": [
            "docker",
            "kubernetes",
            "terraform",
            "aws",
            "ci/cd",
            "python",
            "linux",
            "ansible",
            "prometheus",
            "git",
        ],
        "frontend developer": [
            "javascript",
            "typescript",
            "react",
            "css",
            "html",
            "git",
            "webpack",
            "testing",
            "ci/cd",
            "graphql",
        ],
    }

    _SKILL_CATEGORIES: dict[str, str] = {
        "python": "programming",
        "java": "programming",
        "javascript": "programming",
        "typescript": "programming",
        "r": "programming",
        "sql": "data",
        "spark": "data",
        "airflow": "data",
        "kafka": "data",
        "dbt": "data",
        "pandas": "data",
        "pytorch": "ml",
        "tensorflow": "ml",
        "scikit-learn": "ml",
        "mlflow": "ml",
        "statistics": "ml",
        "docker": "infrastructure",
        "kubernetes": "infrastructure",
        "terraform": "infrastructure",
        "aws": "infrastructure",
        "ci/cd": "infrastructure",
        "linux": "infrastructure",
        "ansible": "infrastructure",
        "prometheus": "infrastructure",
        "redis": "infrastructure",
        "postgresql": "infrastructure",
        "fastapi": "web",
        "react": "web",
        "graphql": "web",
        "css": "web",
        "html": "web",
        "webpack": "web",
        "git": "tools",
        "tableau": "tools",
        "testing": "tools",
    }

    _LEARNING_WEEKS: dict[str, int] = {
        "programming": 8,
        "data": 6,
        "ml": 10,
        "infrastructure": 4,
        "web": 6,
        "tools": 2,
    }

    def __init__(self) -> None:
        self.model_name = "skill-gap-analyzer"
        self.version = "1.0.0"

        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
        except ImportError as exc:
            msg = "SkillGapAnalyzer requires scikit-learn. Install: uv sync --group ml"
            raise MissingDependencyError(msg) from exc

        self._cosine_similarity = cosine_similarity

        documents = []
        self._role_names: list[str] = []
        for role, skills in self._ROLE_SKILL_MAP.items():
            documents.append(" ".join(skills))
            self._role_names.append(role)

        self._vectorizer = TfidfVectorizer()
        self._tfidf_matrix = self._vectorizer.fit_transform(documents)
        self._feature_names = self._vectorizer.get_feature_names_out()

        logger.info(
            "SkillGapAnalyzer trained on %d roles, %d skill features",
            len(self._role_names),
            len(self._feature_names),
        )

    def analyze(
        self,
        user_skills: list[str],
        target_role: str,
        top_k: int = 5,
    ) -> list[SkillRecommendation]:
        """Return top-k skill recommendations for transitioning to *target_role*."""
        role_key = target_role.lower().replace("_", " ")
        target_skills = self._ROLE_SKILL_MAP.get(role_key, [])
        if not target_skills:
            return []

        user_set = {s.lower() for s in user_skills}
        missing = [s for s in target_skills if s.lower() not in user_set]
        if not missing:
            return []

        role_idx = self._role_names.index(role_key)
        role_vector = self._tfidf_matrix[role_idx].toarray().flatten()

        recommendations: list[SkillRecommendation] = []
        for skill in missing:
            feat_idx = None
            for i, name in enumerate(self._feature_names):
                if name == skill.lower().replace("/", ""):
                    feat_idx = i
                    break
            demand = float(role_vector[feat_idx]) if feat_idx is not None else 0.3

            category = self._SKILL_CATEGORIES.get(skill.lower(), "general")
            learning_weeks = self._LEARNING_WEEKS.get(category, 6)
            salary_impact = demand * 15_000

            recommendations.append(
                SkillRecommendation(
                    skill=skill,
                    category=category,
                    demand_score=round(demand, 4),
                    salary_impact=round(salary_impact, 2),
                    learning_time_weeks=learning_weeks,
                ),
            )

        recommendations.sort(key=lambda r: r.demand_score, reverse=True)
        return recommendations[:top_k]


# ======================================================================
# Model 4: Career Path Recommender
# ======================================================================


class CareerPathRecommender:
    """Career path recommendation via graph traversal.

    Builds an adjacency graph from the ``_TRANSITIONS`` table and uses
    BFS to find reachable career transitions from the user's current
    role, sorted by transition probability.

    Pure Python — no ML library dependencies required.
    """

    _TRANSITIONS: dict[tuple[str, str], dict[str, float]] = {
        ("junior developer", "software engineer"): {
            "probability": 0.65,
            "salary_boost": 30_000,
            "years": 2.0,
        },
        ("software engineer", "senior engineer"): {
            "probability": 0.55,
            "salary_boost": 35_000,
            "years": 3.0,
        },
        ("senior engineer", "staff engineer"): {
            "probability": 0.30,
            "salary_boost": 40_000,
            "years": 3.5,
        },
        ("senior engineer", "engineering manager"): {
            "probability": 0.25,
            "salary_boost": 45_000,
            "years": 2.5,
        },
        ("data analyst", "data engineer"): {
            "probability": 0.40,
            "salary_boost": 25_000,
            "years": 1.5,
        },
        ("data engineer", "senior data engineer"): {
            "probability": 0.50,
            "salary_boost": 30_000,
            "years": 2.5,
        },
        ("data engineer", "ml engineer"): {
            "probability": 0.20,
            "salary_boost": 20_000,
            "years": 2.0,
        },
        ("ml engineer", "senior ml engineer"): {
            "probability": 0.45,
            "salary_boost": 35_000,
            "years": 3.0,
        },
        ("data scientist", "senior data scientist"): {
            "probability": 0.50,
            "salary_boost": 30_000,
            "years": 2.5,
        },
        ("data scientist", "ml engineer"): {
            "probability": 0.25,
            "salary_boost": 15_000,
            "years": 1.5,
        },
    }

    def __init__(self) -> None:
        self.model_name = "career-path-recommender"
        self.version = "1.0.0"

        self._graph: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for (from_role, to_role), data in self._TRANSITIONS.items():
            self._graph[from_role].append(
                {
                    "to_role": to_role,
                    "probability": data["probability"],
                    "salary_boost": data["salary_boost"],
                    "years": data["years"],
                }
            )

        logger.info(
            "CareerPathRecommender built graph with %d roles, %d edges",
            len(self._graph),
            len(self._TRANSITIONS),
        )

    def recommend(
        self,
        current_role: str,
        max_paths: int = 3,
    ) -> list[dict[str, Any]]:
        """Return up to *max_paths* career transitions from *current_role*."""
        role_key = current_role.lower().replace("_", " ")
        transitions = self._graph.get(role_key, [])
        if not transitions:
            return []

        sorted_transitions = sorted(
            transitions,
            key=lambda t: t["probability"],
            reverse=True,
        )
        return sorted_transitions[:max_paths]


# ======================================================================
# Model 5: Churn Predictor
# ======================================================================


class ChurnPredictor:
    """User churn prediction using logistic regression.

    Trained on synthetic engagement data derived from the hand-tuned
    weight/bias reference values.  Features:

    - ``days_since_last_login`` — recency signal
    - ``applications_per_day_30d`` — activity signal
    - ``interview_to_apply_ratio`` — quality signal
    - ``profile_completeness`` — investment signal (0-1)
    - ``recent_rejections`` — frustration signal
    """

    _FEATURE_NAMES: list[str] = [
        "days_since_login",
        "applications_per_day",
        "interview_ratio",
        "profile_completeness",
        "recent_rejections",
    ]

    def __init__(self, threshold: float = 0.7, seed: int = 42) -> None:
        self.model_name = "churn-predictor"
        self.version = "1.0.0"
        self.threshold = threshold
        self._seed = seed

        try:
            from sklearn.linear_model import LogisticRegression
        except ImportError as exc:
            msg = "ChurnPredictor requires scikit-learn. Install: uv sync --group ml"
            raise MissingDependencyError(msg) from exc

        X, y = self._generate_training_data()
        self._model = LogisticRegression(
            max_iter=200,
            random_state=seed,
        )
        self._model.fit(X, y)
        logger.info("ChurnPredictor trained on %d synthetic samples", len(X))

    def _generate_training_data(
        self,
    ) -> tuple[list[list[float]], list[int]]:
        """Generate synthetic churn data from hand-tuned weights."""
        rng = random.Random(self._seed)
        X: list[list[float]] = []
        y: list[int] = []

        # Reference weights for synthetic label generation
        weights = [0.015, -0.8, -0.5, -0.6, 0.1]
        bias = -1.5

        for _ in range(500):
            days = rng.randint(0, 120)
            apps = rng.uniform(0, 5)
            ratio = rng.uniform(0, 1)
            profile = rng.uniform(0, 1)
            rejections = rng.randint(0, 15)

            features = [
                float(days),
                apps,
                ratio,
                profile,
                float(rejections),
            ]

            # Compute synthetic label from logistic function
            z = bias + sum(w * f for w, f in zip(weights, features, strict=False))
            prob = 1.0 / (1.0 + math.exp(-z))
            label = 1 if prob > 0.5 else 0

            # Add noise: flip ~5% of labels
            if rng.random() < 0.05:
                label = 1 - label

            X.append(features)
            y.append(label)

        return X, y

    def predict(
        self,
        days_since_last_login: int,
        applications_per_day_30d: float,
        interview_to_apply_ratio: float,
        profile_completeness: float,
        recent_rejections: int,
    ) -> dict[str, Any]:
        """Predict churn probability."""
        features = [
            [
                float(days_since_last_login),
                applications_per_day_30d,
                interview_to_apply_ratio,
                profile_completeness,
                float(recent_rejections),
            ]
        ]

        probability = float(self._model.predict_proba(features)[0][1])
        is_high_risk = probability > self.threshold

        # Identify contributing factors
        coefficients = self._model.coef_[0]
        factors: list[str] = []
        feature_values = features[0]
        for name, coef, val in zip(
            self._FEATURE_NAMES,
            coefficients,
            feature_values,
            strict=False,
        ):
            contribution = coef * val
            if contribution > 0.1:
                factors.append(name)

        return {
            "probability": round(probability, 4),
            "is_high_risk": is_high_risk,
            "threshold": self.threshold,
            "factors": factors,
        }
