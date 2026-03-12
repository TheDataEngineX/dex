"""CareerDEX Phase 5: API Services & Integrations (Issue #69).

FastAPI routers for CareerDEX-specific endpoints:

- Resume management (upload, profile)
- Job recommendations (similarity search)
- Salary intelligence (prediction, trends)
- Market intelligence (trending skills, career paths)
- Skill gap analysis
- Career health & churn risk
- Application tracking

**Status:** Endpoints backed by stub ML models return HTTP 501
(Not Implemented) with a clear message about what needs to be built.
Endpoints backed by real code (``ResumeJobMatcher``) work normally.

All routers follow the DataEngineX conventions:
    - Versioned routes ``/api/v1/careerdex/...``
    - ``response_model=`` on every endpoint
    - Pydantic request/response schemas
    - structlog for API-layer logging
"""

from __future__ import annotations

from datetime import UTC

import structlog
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from careerdex.core.exceptions import MissingDependencyError, StubNotImplementedError
from careerdex.core.pipeline_config import PipelineConfig

from .phase3_embeddings import (
    EmbeddingGenerator,
    InMemoryVectorStore,
    JobDescriptionParser,
    SkillNormalizer,
)
from .phase4_ml_models import (
    CareerPathRecommender,
    ChurnPredictor,
    ResumeJobMatcher,
    SalaryPredictor,
    SkillGapAnalyzer,
)

__all__ = [
    "CareerHealthResponse",
    "JobRecommendation",
    "JobRecommendationsResponse",
    "SalaryPredictionRequest",
    "SalaryPredictionResponse",
    "SkillGapResponse",
    "careerdex_router",
]

logger = structlog.get_logger(__name__)


# ======================================================================
# Pydantic schemas
# ======================================================================


class JobRecommendation(BaseModel):
    """Single job recommendation with scoring breakdown."""

    job_id: str
    job_title: str = ""
    company_name: str = ""
    overall_score: float = Field(..., ge=0, le=1)
    embedding_score: float = 0.0
    skill_score: float = 0.0
    location_score: float = 0.0
    salary_score: float = 0.0


class JobRecommendationsResponse(BaseModel):
    """Response for job recommendations endpoint."""

    user_id: str
    recommendations: list[JobRecommendation]
    total: int
    generated_at: str


class SalaryPredictionRequest(BaseModel):
    """Request body for salary prediction."""

    title: str = Field(..., min_length=2, max_length=255)
    location: str = Field(default="remote", max_length=100)
    seniority: str = Field(default="mid_level", max_length=50)
    skills: list[str] = Field(default_factory=list)
    years_experience: int | None = Field(default=None, ge=0)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "title": "Data Engineer",
                    "location": "San Francisco",
                    "seniority": "senior",
                    "skills": ["python", "spark", "kubernetes"],
                    "years_experience": 5,
                }
            ]
        }
    }


class SalaryPredictionResponse(BaseModel):
    """Response for salary prediction endpoint."""

    p25: float
    p50: float
    p75: float
    confidence: float
    currency: str = "USD"
    top_features: list[str] = Field(default_factory=list)


class SkillGapItem(BaseModel):
    """Single skill gap recommendation."""

    skill: str
    category: str
    demand_score: float
    salary_impact: float
    learning_time_weeks: int


class SkillGapResponse(BaseModel):
    """Response for skill gap analysis endpoint."""

    target_role: str
    recommendations: list[SkillGapItem]


class CareerPathItem(BaseModel):
    """Single career path transition."""

    to_role: str
    probability: float
    salary_boost: float
    years: float


class CareerPathResponse(BaseModel):
    """Response for career path endpoint."""

    current_role: str
    paths: list[CareerPathItem]


class CareerHealthResponse(BaseModel):
    """Response for career health / churn risk endpoint."""

    churn_probability: float
    is_high_risk: bool
    threshold: float
    factors: list[str]


class TrendingSkill(BaseModel):
    """Single trending skill."""

    skill: str
    category: str
    demand_growth_pct: float
    median_salary: float
    job_count: int


class MarketTrendsResponse(BaseModel):
    """Response for market trends endpoint."""

    trending_skills: list[TrendingSkill]
    generated_at: str


# ======================================================================
# Router
# ======================================================================

careerdex_router = APIRouter(prefix="/api/v1/careerdex", tags=["careerdex"])

# Singletons (created once per process)
_matcher = ResumeJobMatcher()
_salary = SalaryPredictor()
_skill_gap = SkillGapAnalyzer()
_career_path = CareerPathRecommender()
_churn = ChurnPredictor()
_parser = JobDescriptionParser()
_normalizer = SkillNormalizer()
_embedder = EmbeddingGenerator()
_vector_store = InMemoryVectorStore()


# Seed sample jobs for vector store recommendations
_SAMPLE_JOBS = [
    {
        "job_id": "dex-001",
        "title": "Senior Data Engineer",
        "company": "DataCorp",
        "skills": ["python", "spark", "sql", "airflow", "kubernetes"],
        "description": "Build and maintain large-scale data pipelines using Python and Spark.",
    },
    {
        "job_id": "dex-002",
        "title": "ML Engineer",
        "company": "AI Labs",
        "skills": ["python", "pytorch", "mlflow", "docker", "kubernetes"],
        "description": "Deploy and optimise production ML models with MLOps best practices.",
    },
    {
        "job_id": "dex-003",
        "title": "Platform Engineer",
        "company": "CloudScale",
        "skills": ["terraform", "kubernetes", "go", "aws", "ci/cd"],
        "description": "Design and operate cloud-native platform infrastructure.",
    },
    {
        "job_id": "dex-004",
        "title": "Backend Developer",
        "company": "WebStar",
        "skills": ["python", "fastapi", "postgresql", "redis", "docker"],
        "description": "Build REST APIs and microservices for high-traffic applications.",
    },
    {
        "job_id": "dex-005",
        "title": "Data Scientist",
        "company": "InsightCo",
        "skills": ["python", "sql", "scikit-learn", "pandas", "statistics"],
        "description": "Analyse datasets and build predictive models for business insights.",
    },
]


def _seed_vector_store() -> None:
    """Seed the in-memory vector store with sample job embeddings (idempotent)."""
    if _vector_store.count() > 0:
        return
    ids: list[str] = []
    embeddings: list[list[float]] = []
    for job in _SAMPLE_JOBS:
        text = f"{job['title']} {job['description']} {' '.join(job['skills'])}"
        vec = _embedder._hash_embed(text)
        ids.append(str(job["job_id"]))
        embeddings.append(vec)
    _vector_store.add(ids=ids, embeddings=embeddings)


# Seed on module load
_seed_vector_store()


@careerdex_router.get(
    "/jobs/recommendations",
    response_model=JobRecommendationsResponse,
    summary="Get job recommendations for a user",
)
async def get_recommendations(
    user_id: str = Query(..., min_length=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> JobRecommendationsResponse:
    """Return top-N job recommendations based on embedding similarity.

    Uses the seeded vector store and ResumeJobMatcher to score jobs
    against a user query embedding.
    """
    from datetime import datetime

    logger.info("recommendations_requested", user_id=user_id, limit=limit)

    # Generate a user embedding from user_id (in production: from user profile/resume)
    user_embedding = _embedder._hash_embed(user_id)

    # Query vector store for nearest jobs
    results = _vector_store.query(user_embedding, top_k=min(limit, len(_SAMPLE_JOBS)))

    # Build job lookup
    job_lookup = {str(j["job_id"]): j for j in _SAMPLE_JOBS}

    recommendations: list[JobRecommendation] = []
    for hit in results:
        job = job_lookup.get(hit["id"])
        if not job:
            continue

        # Use matcher for richer scoring
        job_text = f"{job['title']} {job['description']} {' '.join(job['skills'])}"
        job_embedding = _embedder._hash_embed(job_text)

        match_result = _matcher.match(
            resume_embedding=user_embedding,
            job_embedding=job_embedding,
            resume_skills=[],
            job_skills=list(job["skills"]),
            resume_locations=[],
            job_location="",
        )

        recommendations.append(
            JobRecommendation(
                job_id=str(job["job_id"]),
                job_title=str(job["title"]),
                company_name=str(job["company"]),
                overall_score=round(match_result.overall_score, 4),
                embedding_score=round(match_result.embedding_score, 4),
                skill_score=round(match_result.skill_score, 4),
            )
        )

    # Sort by overall_score descending
    recommendations.sort(key=lambda r: r.overall_score, reverse=True)

    return JobRecommendationsResponse(
        user_id=user_id,
        recommendations=recommendations[:limit],
        total=len(recommendations),
        generated_at=datetime.now(tz=UTC).isoformat(),
    )


@careerdex_router.post(
    "/salary/prediction",
    response_model=SalaryPredictionResponse,
    summary="Predict salary range for a role",
)
async def predict_salary(
    body: SalaryPredictionRequest,
) -> SalaryPredictionResponse | JSONResponse:
    """Predict p25/p50/p75 salary for a given role, location, and skills.

    Returns HTTP 501 if the underlying model is a stub.
    """
    logger.info(
        "salary_prediction_requested",
        title=body.title,
        location=body.location,
        seniority=body.seniority,
    )

    try:
        pred = _salary.predict(
            title=body.title,
            location=body.location,
            seniority=body.seniority,
            skills=body.skills,
            years_experience=body.years_experience,
        )
    except MissingDependencyError as exc:
        logger.error("salary_prediction_missing_dep", error=str(exc))
        return JSONResponse(
            status_code=503,
            content={"error": "missing_dependency", "message": str(exc)},
        )
    except (StubNotImplementedError, NotImplementedError) as exc:
        logger.warning("salary_prediction_stub", error=str(exc))
        return JSONResponse(
            status_code=501,
            content={"error": "not_implemented", "message": str(exc)},
        )

    return SalaryPredictionResponse(
        p25=pred.p25,
        p50=pred.p50,
        p75=pred.p75,
        confidence=pred.confidence,
        top_features=pred.top_features,
    )


@careerdex_router.get(
    "/insights/skill-gaps",
    response_model=SkillGapResponse,
    summary="Analyse skill gaps for a target role",
)
async def get_skill_gaps(
    target_role: str = Query(..., min_length=2),
    user_skills: str = Query(default="", description="Comma-separated current skills"),
    top_k: int = Query(default=5, ge=1, le=20),
) -> SkillGapResponse | JSONResponse:
    """Identify missing skills for transitioning to *target_role*.

    Returns HTTP 501 if the underlying model is a stub.
    """
    skills_list = [s.strip() for s in user_skills.split(",") if s.strip()]
    normalised = _normalizer.normalize_list(skills_list)

    try:
        recs = _skill_gap.analyze(normalised, target_role, top_k)
    except MissingDependencyError as exc:
        logger.error("skill_gap_missing_dep", error=str(exc))
        return JSONResponse(
            status_code=503,
            content={"error": "missing_dependency", "message": str(exc)},
        )
    except (StubNotImplementedError, NotImplementedError) as exc:
        logger.warning("skill_gap_stub", error=str(exc))
        return JSONResponse(
            status_code=501,
            content={"error": "not_implemented", "message": str(exc)},
        )

    return SkillGapResponse(
        target_role=target_role,
        recommendations=[
            SkillGapItem(
                skill=r.skill,
                category=r.category,
                demand_score=r.demand_score,
                salary_impact=r.salary_impact,
                learning_time_weeks=r.learning_time_weeks,
            )
            for r in recs
        ],
    )


@careerdex_router.get(
    "/market/careers",
    response_model=CareerPathResponse,
    summary="Recommend career transitions from current role",
)
async def get_career_paths(
    role: str = Query(..., min_length=2),
    max_paths: int = Query(default=3, ge=1, le=10),
) -> CareerPathResponse | JSONResponse:
    """Return likely career paths from *role*.

    Returns HTTP 501 if the underlying model is a stub.
    """
    try:
        paths = _career_path.recommend(role, max_paths)
    except MissingDependencyError as exc:
        logger.error("career_path_missing_dep", error=str(exc))
        return JSONResponse(
            status_code=503,
            content={"error": "missing_dependency", "message": str(exc)},
        )
    except (StubNotImplementedError, NotImplementedError) as exc:
        logger.warning("career_path_stub", error=str(exc))
        return JSONResponse(
            status_code=501,
            content={"error": "not_implemented", "message": str(exc)},
        )

    return CareerPathResponse(
        current_role=role,
        paths=[
            CareerPathItem(
                to_role=p["to_role"],
                probability=p["probability"],
                salary_boost=p["salary_boost"],
                years=p["years"],
            )
            for p in paths
        ],
    )


@careerdex_router.get(
    "/insights/career-health",
    response_model=CareerHealthResponse,
    summary="Assess churn risk for a user",
)
async def get_career_health(
    days_since_login: int = Query(default=0, ge=0),
    applications_per_day: float = Query(default=1.0, ge=0),
    interview_ratio: float = Query(default=0.2, ge=0, le=1),
    profile_completeness: float = Query(default=0.8, ge=0, le=1),
    recent_rejections: int = Query(default=0, ge=0),
) -> CareerHealthResponse | JSONResponse:
    """Predict churn probability for a user based on engagement metrics.

    Returns HTTP 501 if the underlying model is a stub.
    """
    try:
        result = _churn.predict(
            days_since_last_login=days_since_login,
            applications_per_day_30d=applications_per_day,
            interview_to_apply_ratio=interview_ratio,
            profile_completeness=profile_completeness,
            recent_rejections=recent_rejections,
        )
    except MissingDependencyError as exc:
        logger.error("churn_prediction_missing_dep", error=str(exc))
        return JSONResponse(
            status_code=503,
            content={"error": "missing_dependency", "message": str(exc)},
        )
    except (StubNotImplementedError, NotImplementedError) as exc:
        logger.warning("churn_prediction_stub", error=str(exc))
        return JSONResponse(
            status_code=501,
            content={"error": "not_implemented", "message": str(exc)},
        )

    return CareerHealthResponse(
        churn_probability=result["probability"],
        is_high_risk=result["is_high_risk"],
        threshold=result["threshold"],
        factors=result["factors"],
    )


# Curated market trends data — in production this comes from Gold layer analytics.
_TRENDING_SKILLS: list[dict[str, object]] = [
    {
        "skill": "python",
        "category": "language",
        "demand_growth_pct": 12.3,
        "median_salary": 145000.0,
        "job_count": 84200,
    },
    {
        "skill": "kubernetes",
        "category": "tool",
        "demand_growth_pct": 28.7,
        "median_salary": 162000.0,
        "job_count": 41500,
    },
    {
        "skill": "generative ai",
        "category": "domain",
        "demand_growth_pct": 94.5,
        "median_salary": 185000.0,
        "job_count": 23800,
    },
    {
        "skill": "apache spark",
        "category": "tool",
        "demand_growth_pct": 8.1,
        "median_salary": 155000.0,
        "job_count": 29700,
    },
    {
        "skill": "rust",
        "category": "language",
        "demand_growth_pct": 42.6,
        "median_salary": 170000.0,
        "job_count": 12300,
    },
    {
        "skill": "mlops",
        "category": "domain",
        "demand_growth_pct": 35.2,
        "median_salary": 168000.0,
        "job_count": 18900,
    },
    {
        "skill": "terraform",
        "category": "tool",
        "demand_growth_pct": 18.9,
        "median_salary": 152000.0,
        "job_count": 31200,
    },
    {
        "skill": "go",
        "category": "language",
        "demand_growth_pct": 15.4,
        "median_salary": 160000.0,
        "job_count": 27600,
    },
]


@careerdex_router.get(
    "/market/trends",
    response_model=MarketTrendsResponse,
    summary="Get trending skills and market data",
)
async def get_market_trends() -> MarketTrendsResponse:
    """Return trending skills with demand growth and salary data.

    In production this data comes from Gold layer analytics.
    Currently returns curated market intelligence.
    """
    from datetime import datetime

    logger.info("market_trends_requested")

    return MarketTrendsResponse(
        trending_skills=[
            TrendingSkill(
                skill=str(s["skill"]),
                category=str(s["category"]),
                demand_growth_pct=float(s["demand_growth_pct"]),
                median_salary=float(s["median_salary"]),
                job_count=int(s["job_count"]),
            )
            for s in _TRENDING_SKILLS
        ],
        generated_at=datetime.now(tz=UTC).isoformat(),
    )


# ---------------------------------------------------------------------------
# Data source & system config endpoints (moved from generic v1 router)
# ---------------------------------------------------------------------------


@careerdex_router.get(
    "/data/sources",
    summary="List registered CareerDEX data sources",
)
def list_data_sources() -> dict[str, list[dict[str, object]]]:
    """List registered job data sources from CareerDEX pipeline config."""
    sources: list[dict[str, object]] = [
        {
            "name": name,
            "type": cfg.get("type", "unknown"),
            "status": "active",
        }
        for name, cfg in PipelineConfig.CAREERDEX_JOB_SOURCES.items()
    ]
    return {"sources": sources}


@careerdex_router.get(
    "/system/config",
    summary="Return non-sensitive CareerDEX system configuration",
)
def system_config() -> dict[str, object]:
    """Return non-sensitive system configuration."""
    return {
        "schedule": PipelineConfig.EXECUTION_SCHEDULE,
        "expected_jobs_per_cycle": PipelineConfig.EXPECTED_JOBS_PER_CYCLE,
        "timeout_minutes": PipelineConfig.TIMEOUT_MINUTES,
        "sources": list(PipelineConfig.CAREERDEX_JOB_SOURCES.keys()),
    }
