"""Tests for CareerDEX phases 1–6.

Covers:
    - Phase 0: Settings / exceptions / config validation
    - Phase 1: config loading, schemas, validators, medallion
    - Phase 2: connectors, dedup, ingestion pipeline
    - Phase 3: job parsing, resume parsing, skill normaliser, embeddings, vector store
    - Phase 4: all 5 ML models
    - Phase 5: API endpoints via TestClient
    - Phase 6: deployment config, monitoring, security audit
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from careerdex.core.exceptions import MissingDependencyError, StubNotImplementedError

# ============================================================================
# Phase 0 — Settings & Exceptions
# ============================================================================


class TestCareerDEXSettings:
    """Test Pydantic-validated settings."""

    def test_load_default_settings(self) -> None:
        from careerdex.core.settings import CareerDEXSettings, reset_settings

        reset_settings()  # clear cached singleton
        settings = CareerDEXSettings.load()
        assert settings.pipeline.name == "careerdex-job-ingestion"
        assert len(settings.sources) > 0
        assert "bronze" in settings.storage.layers
        assert "silver" in settings.storage.layers
        assert "gold" in settings.storage.layers

    def test_missing_config_raises(self, tmp_path: Path) -> None:
        from careerdex.core.exceptions import ConfigurationError
        from careerdex.core.settings import CareerDEXSettings

        with pytest.raises(ConfigurationError, match="config file not found"):
            CareerDEXSettings.load(tmp_path / "nonexistent.json")

    def test_singleton_accessor(self) -> None:
        from careerdex.core.settings import get_settings, reset_settings

        reset_settings()
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2  # same instance
        reset_settings()


# ============================================================================
# Phase 1 — Foundation
# ============================================================================


class TestLoadConfig:
    """Test config loading helper."""

    def test_load_default_config(self) -> None:
        from careerdex.phases.phase1_foundation import load_config

        cfg = load_config()
        assert "pipeline" in cfg
        assert "sources" in cfg
        assert cfg["pipeline"]["name"] == "careerdex-job-ingestion"

    def test_load_missing_config_raises(self, tmp_path: Path) -> None:
        from careerdex.phases.phase1_foundation import load_config

        with pytest.raises(FileNotFoundError, match="Config file not found"):
            load_config(tmp_path / "nonexistent.json")


class TestPhase1Foundation:
    """Test Phase 1 bootstrap."""

    def test_bootstrap_succeeds(self) -> None:
        from careerdex.phases.phase1_foundation import Phase1Foundation

        p1 = Phase1Foundation()
        result = p1.bootstrap()
        assert result["status"] == "success"
        assert len(result["components"]) > 0
        assert len(result["errors"]) == 0

    def test_bootstrap_step_results(self) -> None:
        from careerdex.phases.phase1_foundation import Phase1Foundation

        p1 = Phase1Foundation()
        result = p1.bootstrap()
        step_names = [s["name"] for s in result["steps"]]
        assert "schemas" in step_names
        assert "validators" in step_names
        assert "medallion" in step_names
        assert "pipeline_config" in step_names

    def test_get_sample_jobs(self) -> None:
        from careerdex.phases.phase1_foundation import get_sample_jobs

        jobs = get_sample_jobs()
        assert len(jobs) == 5
        assert all("job_id" in j for j in jobs)
        assert all("dex_hash" in j for j in jobs)

    def test_bootstrap_convenience_function(self) -> None:
        from careerdex.phases.phase1_foundation import bootstrap_phase1

        result = bootstrap_phase1()
        assert result["status"] == "success"


# ============================================================================
# Phase 2 — Job Ingestion
# ============================================================================


class TestJobSourceConnector:
    """Test connector ABC and concrete implementations."""

    def test_linkedin_connector_attributes(self) -> None:
        from careerdex.phases.phase2_job_ingestion import LinkedInConnector

        conn = LinkedInConnector()
        assert conn.source.value == "linkedin"
        assert conn.batch_size > 0

    def test_indeed_connector_fetch_raises(self) -> None:
        from careerdex.phases.phase2_job_ingestion import IndeedConnector

        conn = IndeedConnector()
        with pytest.raises(StubNotImplementedError):
            conn.fetch()

    def test_linkedin_normalize(self) -> None:
        from careerdex.phases.phase2_job_ingestion import LinkedInConnector

        conn = LinkedInConnector()
        raw = {
            "id": "li_123",
            "title": "Data Engineer",
            "company": {"name": "TestCo"},
            "description": "Build pipelines.",
            "location": {"country": "US", "city": "SF"},
        }
        norm = conn.normalize(raw)
        assert norm["job_title"] == "Data Engineer"
        assert norm["source"] == "linkedin"
        assert norm["dex_hash"]

    def test_glassdoor_normalize(self) -> None:
        from careerdex.phases.phase2_job_ingestion import GlassdoorConnector

        conn = GlassdoorConnector()
        raw = {
            "id": "gd_456",
            "jobTitle": "ML Engineer",
            "employer": {"name": "Acme"},
            "description": "Train models.",
        }
        norm = conn.normalize(raw)
        assert norm["job_title"] == "ML Engineer"
        assert norm["source"] == "glassdoor"


class TestLocalFileConnectors:
    """Test JSON and CSV file-based connectors."""

    def test_json_connector_fetch(self, tmp_path: Path) -> None:
        from careerdex.phases.phase2_job_ingestion import JsonFileConnector

        data = [
            {"id": "j1", "company": "Co", "title": "Dev", "description": "Build stuff."},
            {"id": "j2", "company": "Co2", "title": "Eng", "description": "Ship things."},
        ]
        f = tmp_path / "jobs.json"
        f.write_text(json.dumps(data))
        conn = JsonFileConnector(f)
        jobs, errors = conn.fetch()
        assert len(jobs) == 2
        assert not errors
        assert conn.fetch_count == 2
        assert conn.source.value == "local_json"

    def test_json_connector_normalize(self, tmp_path: Path) -> None:
        from careerdex.phases.phase2_job_ingestion import JsonFileConnector

        f = tmp_path / "jobs.json"
        f.write_text("[]")
        conn = JsonFileConnector(f)
        raw = {
            "id": "j1",
            "company": "Acme",
            "title": "Data Engineer",
            "description": "Build pipelines with Python and Spark.",
            "location": {"country": "US", "city": "Seattle"},
        }
        norm = conn.normalize(raw)
        assert norm["job_title"] == "Data Engineer"
        assert norm["company_name"] == "Acme"
        assert norm["source"] == "local_json"
        assert norm["dex_hash"]
        assert norm["location"]["city"] == "Seattle"

    def test_json_connector_missing_file(self, tmp_path: Path) -> None:
        from careerdex.phases.phase2_job_ingestion import JsonFileConnector

        conn = JsonFileConnector(tmp_path / "nonexistent.json")
        jobs, errors = conn.fetch()
        assert len(jobs) == 0
        assert len(errors) == 1
        assert "not found" in errors[0].lower()

    def test_json_connector_invalid_json(self, tmp_path: Path) -> None:
        from careerdex.phases.phase2_job_ingestion import JsonFileConnector

        f = tmp_path / "bad.json"
        f.write_text("{not valid json")
        conn = JsonFileConnector(f)
        jobs, errors = conn.fetch()
        assert len(jobs) == 0
        assert len(errors) == 1

    def test_json_connector_not_array(self, tmp_path: Path) -> None:
        from careerdex.phases.phase2_job_ingestion import JsonFileConnector

        f = tmp_path / "obj.json"
        f.write_text('{"key": "value"}')
        conn = JsonFileConnector(f)
        jobs, errors = conn.fetch()
        assert len(jobs) == 0
        assert "array" in errors[0].lower()

    def test_json_connector_string_location(self, tmp_path: Path) -> None:
        from careerdex.phases.phase2_job_ingestion import JsonFileConnector

        f = tmp_path / "jobs.json"
        f.write_text("[]")
        conn = JsonFileConnector(f)
        raw = {"id": "j1", "company": "Co", "title": "Dev", "description": "x", "location": "NYC"}
        norm = conn.normalize(raw)
        assert norm["location"]["city"] == "NYC"

    def test_csv_connector_fetch(self, tmp_path: Path) -> None:
        from careerdex.phases.phase2_job_ingestion import CsvFileConnector

        f = tmp_path / "jobs.csv"
        f.write_text(
            "id,company,title,description,city,country,employment_type\n"
            "c1,TechCo,Dev,Build stuff.,Austin,US,full_time\n"
            "c2,DataCo,Eng,Ship things.,SF,US,contract\n"
        )
        conn = CsvFileConnector(f)
        jobs, errors = conn.fetch()
        assert len(jobs) == 2
        assert not errors
        assert conn.fetch_count == 2
        assert conn.source.value == "local_csv"

    def test_csv_connector_normalize(self, tmp_path: Path) -> None:
        from careerdex.phases.phase2_job_ingestion import CsvFileConnector

        f = tmp_path / "jobs.csv"
        f.write_text("id\nc1\n")
        conn = CsvFileConnector(f)
        raw = {
            "id": "c1",
            "company": "Acme",
            "title": "Data Analyst",
            "description": "Analyze data.",
            "city": "Chicago",
            "country": "US",
            "employment_type": "full_time",
        }
        norm = conn.normalize(raw)
        assert norm["job_title"] == "Data Analyst"
        assert norm["source"] == "local_csv"
        assert norm["location"]["city"] == "Chicago"
        assert norm["dex_hash"]

    def test_csv_connector_missing_file(self, tmp_path: Path) -> None:
        from careerdex.phases.phase2_job_ingestion import CsvFileConnector

        conn = CsvFileConnector(tmp_path / "nonexistent.csv")
        jobs, errors = conn.fetch()
        assert len(jobs) == 0
        assert len(errors) == 1

    def test_pipeline_with_local_connectors(self, tmp_path: Path) -> None:
        from careerdex.phases.phase2_job_ingestion import (
            CsvFileConnector,
            JobIngestionPipeline,
            JsonFileConnector,
        )

        json_file = tmp_path / "jobs.json"
        json_file.write_text(
            json.dumps(
                [
                    {
                        "id": "j1",
                        "company": "Co",
                        "title": "Dev",
                        "description": "Build Python applications and services.",
                    },
                    {
                        "id": "j2",
                        "company": "Co2",
                        "title": "Eng",
                        "description": "Ship containerized microservices to production.",
                    },
                ]
            )
        )
        csv_file = tmp_path / "jobs.csv"
        csv_file.write_text(
            "id,company,title,description,city,country,employment_type\n"
            "c1,TechCo,QA,Test all the things and find all the bugs.,Austin,US,full_time\n"
        )
        pipeline = JobIngestionPipeline(
            connectors=[JsonFileConnector(json_file), CsvFileConnector(csv_file)]
        )
        summary = pipeline.run_cycle()
        assert summary["total_fetched"] == 3
        assert summary["after_dedup"] == 3
        assert summary["scored"] == 3
        assert not summary["errors"]

    def test_pipeline_with_fixture_files(self) -> None:
        from careerdex.phases.phase2_job_ingestion import (
            CsvFileConnector,
            JobIngestionPipeline,
            JsonFileConnector,
        )

        fixtures = Path(__file__).parent.parent / "fixtures"
        pipeline = JobIngestionPipeline(
            connectors=[
                JsonFileConnector(fixtures / "sample_jobs.json"),
                CsvFileConnector(fixtures / "sample_jobs.csv"),
            ]
        )
        summary = pipeline.run_cycle()
        assert summary["total_fetched"] == 10
        assert summary["after_dedup"] == 10
        assert summary["scored"] == 10
        assert not summary["errors"]


class TestDeduplicationEngine:
    """Test hash-based deduplication."""

    def test_removes_duplicates(self) -> None:
        from careerdex.phases.phase2_job_ingestion import DeduplicationEngine

        dedup = DeduplicationEngine()
        jobs = [
            {"job_id": "1", "dex_hash": "aaa"},
            {"job_id": "2", "dex_hash": "bbb"},
            {"job_id": "3", "dex_hash": "aaa"},  # duplicate
        ]
        result = dedup.deduplicate(jobs)
        assert len(result) == 2
        assert dedup.seen_count == 2

    def test_empty_hash_skipped(self) -> None:
        from careerdex.phases.phase2_job_ingestion import DeduplicationEngine

        dedup = DeduplicationEngine()
        jobs = [{"job_id": "1", "dex_hash": ""}]
        result = dedup.deduplicate(jobs)
        assert len(result) == 0


class TestJobIngestionPipeline:
    """Test the ingestion orchestrator."""

    def test_run_cycle_raises_because_connectors_are_stubs(self) -> None:
        from careerdex.phases.phase2_job_ingestion import JobIngestionPipeline

        pipeline = JobIngestionPipeline()
        # run_cycle calls connector.fetch() which raises StubNotImplementedError
        # The pipeline catches errors per-connector, so it should still return a summary
        # with zero fetched jobs and errors recorded.
        summary = pipeline.run_cycle()
        assert "cycle_start" in summary
        assert "total_fetched" in summary
        assert summary["total_fetched"] == 0
        assert isinstance(summary["errors"], list)
        # All 4 connectors are stubs, so we expect 4 errors
        assert len(summary["errors"]) >= 1


# ============================================================================
# Phase 3 — Feature Engineering & Embeddings
# ============================================================================


class TestJobDescriptionParser:
    """Test job description parsing."""

    def test_extract_skills(self) -> None:
        from careerdex.phases.phase3_embeddings import JobDescriptionParser

        parser = JobDescriptionParser()
        result = parser.parse("Data Engineer", "We need Python, SQL, and Spark experience.")
        assert "python" in result.skills
        assert "sql" in result.skills
        assert "spark" in result.skills

    def test_detect_seniority(self) -> None:
        from careerdex.phases.phase3_embeddings import JobDescriptionParser

        parser = JobDescriptionParser()
        result = parser.parse("Senior Data Engineer", "Lead the team.")
        assert result.seniority == "senior"

    def test_extract_salary(self) -> None:
        from careerdex.phases.phase3_embeddings import JobDescriptionParser

        parser = JobDescriptionParser()
        result = parser.parse("Engineer", "Salary range: $120,000 - $180,000 per year.")
        assert result.salary_min == 120000.0
        assert result.salary_max == 180000.0

    def test_detect_remote(self) -> None:
        from careerdex.phases.phase3_embeddings import JobDescriptionParser

        parser = JobDescriptionParser()
        result = parser.parse("Engineer", "This is a fully remote position.")
        assert result.remote is True

    def test_no_salary_returns_none(self) -> None:
        from careerdex.phases.phase3_embeddings import JobDescriptionParser

        parser = JobDescriptionParser()
        result = parser.parse("Engineer", "No salary mentioned.")
        assert result.salary_min is None


class TestResumeParser:
    """Test resume text parsing."""

    def test_extract_email(self) -> None:
        from careerdex.phases.phase3_embeddings import ResumeParser

        parser = ResumeParser()
        result = parser.parse("John Doe, john@example.com, (555) 123-4567, Python, Docker")
        assert result.email == "john@example.com"
        assert result.phone == "(555) 123-4567"
        assert "python" in result.skills


class TestSkillNormalizer:
    """Test skill normalisation and categorisation."""

    def test_normalize_alias(self) -> None:
        from careerdex.phases.phase3_embeddings import SkillNormalizer

        norm = SkillNormalizer()
        assert norm.normalize("js") == "javascript"
        assert norm.normalize("k8s") == "kubernetes"
        assert norm.normalize("Python") == "python"

    def test_categorize(self) -> None:
        from careerdex.phases.phase3_embeddings import SkillNormalizer

        norm = SkillNormalizer()
        assert norm.categorize("python") == "language"
        assert norm.categorize("docker") == "tool"
        assert norm.categorize("aws") == "platform"
        assert norm.categorize("unknown_skill") == "other"

    def test_normalize_list_deduplicates(self) -> None:
        from careerdex.phases.phase3_embeddings import SkillNormalizer

        norm = SkillNormalizer()
        result = norm.normalize_list(["js", "JavaScript", "python"])
        assert result == ["javascript", "python"]


class TestEmbeddingGenerator:
    """Test embedding generation (hash fallback).

    These tests mock sentence-transformers import so _hash_embed uses
    the user-specified dimension rather than the real model dimension.
    """

    @staticmethod
    def _make_generator(dimension: int = 64) -> Any:
        """Create an EmbeddingGenerator with sentence-transformers mocked out."""
        import importlib
        import sys

        # Temporarily hide sentence_transformers so the generator falls back
        saved = sys.modules.get("sentence_transformers")
        sys.modules["sentence_transformers"] = None  # type: ignore[assignment]
        try:
            # Re-import the module to pick up the mocked import
            import careerdex.phases.phase3_embeddings as mod

            importlib.reload(mod)
            gen = mod.EmbeddingGenerator(dimension=dimension)
        finally:
            # Restore original
            if saved is not None:
                sys.modules["sentence_transformers"] = saved
            else:
                sys.modules.pop("sentence_transformers", None)
            importlib.reload(mod)
        return gen

    def test_embed_returns_correct_dimension(self) -> None:
        gen = self._make_generator(dimension=64)
        vec = gen._hash_embed("test text")
        assert len(vec) == 64

    def test_embed_raises_without_sentence_transformers(self) -> None:
        gen = self._make_generator(dimension=64)
        assert gen._model is None
        with pytest.raises(MissingDependencyError):
            gen.embed("test text")

    def test_embed_batch_raises_without_sentence_transformers(self) -> None:
        gen = self._make_generator(dimension=64)
        assert gen._model is None
        with pytest.raises(MissingDependencyError):
            gen.embed_batch(["text 1", "text 2"])

    def test_hash_embed_is_normalised(self) -> None:
        import math

        gen = self._make_generator(dimension=32)
        vec = gen._hash_embed("test text")
        norm = math.sqrt(sum(x * x for x in vec))
        assert abs(norm - 1.0) < 0.01

    def test_hash_embed_batch(self) -> None:
        gen = self._make_generator(dimension=32)
        vecs = [gen._hash_embed(t) for t in ["text 1", "text 2", "text 3"]]
        assert len(vecs) == 3
        assert all(len(v) == 32 for v in vecs)

    def test_hash_embed_deterministic(self) -> None:
        gen = self._make_generator(dimension=32)
        v1 = gen._hash_embed("the same text")
        v2 = gen._hash_embed("the same text")
        assert v1 == v2


class TestInMemoryVectorStore:
    """Test in-memory vector store."""

    def test_add_and_query(self) -> None:
        from careerdex.phases.phase3_embeddings import InMemoryVectorStore

        store = InMemoryVectorStore()
        store.add(
            ids=["a", "b"],
            embeddings=[[1.0, 0.0], [0.0, 1.0]],
        )
        assert store.count() == 2
        results = store.query([1.0, 0.0], top_k=1)
        assert results[0]["id"] == "a"

    def test_delete(self) -> None:
        from careerdex.phases.phase3_embeddings import InMemoryVectorStore

        store = InMemoryVectorStore()
        store.add(ids=["x"], embeddings=[[1.0]])
        assert store.count() == 1
        assert store.delete(["x"]) == 1
        assert store.count() == 0


# ============================================================================
# Phase 4 — ML Models
# ============================================================================


class TestResumeJobMatcher:
    """Test resume-job matching."""

    def test_perfect_match(self) -> None:
        from careerdex.phases.phase4_ml_models import ResumeJobMatcher

        matcher = ResumeJobMatcher()
        result = matcher.match(
            resume_embedding=[1.0, 0.0, 0.0],
            job_embedding=[1.0, 0.0, 0.0],
            resume_skills=["python", "sql"],
            job_skills=["python", "sql"],
            resume_locations=["San Francisco"],
            job_location="San Francisco",
            salary_expectation=150000,
            salary_min=140000,
            salary_max=170000,
        )
        assert result.overall_score > 0.9
        assert result.embedding_score == 1.0
        assert result.skill_score == 1.0

    def test_no_skills_overlap(self) -> None:
        from careerdex.phases.phase4_ml_models import ResumeJobMatcher

        matcher = ResumeJobMatcher()
        result = matcher.match(
            resume_embedding=[1.0, 0.0],
            job_embedding=[0.0, 1.0],
            resume_skills=["java"],
            job_skills=["python", "sql"],
            resume_locations=["Austin"],
            job_location="New York",
        )
        assert result.skill_score == 0.0


class TestSalaryPredictor:
    """Test salary prediction with XGBoost."""

    def test_predict_returns_valid_ranges(self) -> None:
        from careerdex.phases.phase4_ml_models import SalaryPredictor

        predictor = SalaryPredictor()
        result = predictor.predict(
            "Data Engineer",
            location="San Francisco",
            seniority="senior",
        )
        assert result.p25 > 0
        assert result.p25 <= result.p50 <= result.p75
        assert 0 <= result.confidence <= 1
        assert len(result.top_features) > 0

    def test_predict_unknown_title_still_works(self) -> None:
        from careerdex.phases.phase4_ml_models import SalaryPredictor

        predictor = SalaryPredictor()
        result = predictor.predict("Unicorn Wrangler")
        assert result.p50 > 0


class TestSkillGapAnalyzer:
    """Test skill gap analysis with TF-IDF."""

    def test_analyze_returns_recommendations(self) -> None:
        from careerdex.phases.phase4_ml_models import SkillGapAnalyzer

        analyzer = SkillGapAnalyzer()
        recs = analyzer.analyze(
            user_skills=["python", "sql"],
            target_role="Data Engineer",
            top_k=3,
        )
        assert len(recs) > 0
        assert len(recs) <= 3
        for r in recs:
            assert r.skill not in ("python", "sql")
            assert r.demand_score > 0
            assert r.learning_time_weeks > 0

    def test_analyze_unknown_role_returns_empty(self) -> None:
        from careerdex.phases.phase4_ml_models import SkillGapAnalyzer

        analyzer = SkillGapAnalyzer()
        recs = analyzer.analyze(["python"], "Nonexistent Role XYZ", top_k=5)
        assert recs == []


class TestCareerPathRecommender:
    """Test career path recommender with graph traversal."""

    def test_recommend_returns_transitions(self) -> None:
        from careerdex.phases.phase4_ml_models import CareerPathRecommender

        rec = CareerPathRecommender()
        paths = rec.recommend("data engineer", max_paths=3)
        assert len(paths) > 0
        for p in paths:
            assert "to_role" in p
            assert 0 < p["probability"] <= 1
            assert "salary_boost" in p
            assert "years" in p

    def test_recommend_unknown_role_returns_empty(self) -> None:
        from careerdex.phases.phase4_ml_models import CareerPathRecommender

        rec = CareerPathRecommender()
        paths = rec.recommend("nonexistent role xyz")
        assert paths == []


class TestChurnPredictor:
    """Test churn prediction with logistic regression."""

    def test_predict_returns_probability(self) -> None:
        from careerdex.phases.phase4_ml_models import ChurnPredictor

        predictor = ChurnPredictor()
        result = predictor.predict(
            days_since_last_login=1,
            applications_per_day_30d=2.0,
            interview_to_apply_ratio=0.3,
            profile_completeness=0.9,
            recent_rejections=0,
        )
        assert 0 <= result["probability"] <= 1
        assert isinstance(result["is_high_risk"], bool)
        assert isinstance(result["factors"], list)

    def test_high_risk_user(self) -> None:
        from careerdex.phases.phase4_ml_models import ChurnPredictor

        predictor = ChurnPredictor()
        result = predictor.predict(
            days_since_last_login=90,
            applications_per_day_30d=0.0,
            interview_to_apply_ratio=0.0,
            profile_completeness=0.2,
            recent_rejections=10,
        )
        # Disengaged user should have higher churn probability
        assert result["probability"] > 0.3


# ============================================================================
# Phase 5 — API Services
# ============================================================================


class TestCareerDEXAPI:
    """Test CareerDEX API endpoints via TestClient."""

    @pytest.fixture()
    def client(self) -> TestClient:
        from careerdex.api.main import app

        return TestClient(app)

    def test_salary_prediction_returns_200(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/careerdex/salary/prediction",
            json={
                "title": "Data Engineer",
                "location": "San Francisco",
                "seniority": "senior",
                "skills": ["python", "spark"],
                "years_experience": 5,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["p25"] <= data["p50"] <= data["p75"]
        assert 0 <= data["confidence"] <= 1

    def test_skill_gaps_returns_200(self, client: TestClient) -> None:
        resp = client.get(
            "/api/v1/careerdex/insights/skill-gaps",
            params={"target_role": "data engineer", "user_skills": "python,sql", "top_k": 3},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["target_role"] == "data engineer"
        assert isinstance(data["recommendations"], list)

    def test_career_paths_returns_200(self, client: TestClient) -> None:
        resp = client.get(
            "/api/v1/careerdex/market/careers",
            params={"role": "data engineer"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["current_role"] == "data engineer"
        assert isinstance(data["paths"], list)

    def test_career_health_returns_200(self, client: TestClient) -> None:
        resp = client.get(
            "/api/v1/careerdex/insights/career-health",
            params={"days_since_login": 1, "profile_completeness": 0.9},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert 0 <= data["churn_probability"] <= 1
        assert isinstance(data["is_high_risk"], bool)
        assert isinstance(data["factors"], list)

    def test_market_trends_returns_200(self, client: TestClient) -> None:
        resp = client.get("/api/v1/careerdex/market/trends")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["trending_skills"], list)
        assert len(data["trending_skills"]) > 0
        skill = data["trending_skills"][0]
        assert "skill" in skill
        assert "demand_growth_pct" in skill
        assert "median_salary" in skill
        assert "job_count" in skill
        assert "generated_at" in data

    def test_recommendations_returns_200(self, client: TestClient) -> None:
        resp = client.get(
            "/api/v1/careerdex/jobs/recommendations",
            params={"user_id": "test-user-123"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == "test-user-123"
        assert isinstance(data["recommendations"], list)
        assert len(data["recommendations"]) > 0
        rec = data["recommendations"][0]
        assert "job_id" in rec
        assert "job_title" in rec
        assert "overall_score" in rec
        assert "generated_at" in data


# ============================================================================
# Phase 6 — Testing & Deployment
# ============================================================================


class TestDeploymentConfig:
    """Test deployment configuration."""

    def test_generate_dev_config(self) -> None:
        from careerdex.phases.phase6_testing_deployment import generate_deployment_config

        cfg = generate_deployment_config(env="dev")
        assert cfg.replicas == 1
        assert cfg.env_vars["ENVIRONMENT"] == "dev"

    def test_generate_prod_config(self) -> None:
        from careerdex.phases.phase6_testing_deployment import generate_deployment_config

        cfg = generate_deployment_config(env="prod", image_tag="v0.5.0")
        assert cfg.replicas == 3
        assert "v0.5.0" in cfg.image

    def test_to_k8s_env(self) -> None:
        from careerdex.phases.phase6_testing_deployment import DeploymentConfig

        cfg = DeploymentConfig(env_vars={"FOO": "bar", "BAZ": "qux"})
        env_list = cfg.to_k8s_env()
        assert len(env_list) == 2
        assert all("name" in e and "value" in e for e in env_list)


class TestMonitoringConfig:
    """Test monitoring and alerting setup."""

    def test_default_rules(self) -> None:
        from careerdex.phases.phase6_testing_deployment import MonitoringConfig

        config = MonitoringConfig.default()
        assert len(config.alert_rules) == 5

    def test_rules_yaml_format(self) -> None:
        from careerdex.phases.phase6_testing_deployment import MonitoringConfig

        config = MonitoringConfig.default()
        rules = config.all_rules_yaml()
        assert all("alert" in r for r in rules)
        assert all("expr" in r for r in rules)


class TestSecurityAudit:
    """Test security audit helpers."""

    def test_detect_hardcoded_secret(self) -> None:
        from careerdex.phases.phase6_testing_deployment import SecurityAudit

        files = {"bad.py": 'API_KEY = "sk-1234567890abcdef"'}
        passed, findings = SecurityAudit.check_no_hardcoded_secrets(files)
        assert passed is False
        assert len(findings) > 0

    def test_clean_files_pass(self) -> None:
        from careerdex.phases.phase6_testing_deployment import SecurityAudit

        files = {"good.py": 'api_key = os.getenv("API_KEY")'}
        passed, findings = SecurityAudit.check_no_hardcoded_secrets(files)
        assert passed is True

    def test_detect_sql_injection(self) -> None:
        from careerdex.phases.phase6_testing_deployment import SecurityAudit

        files = {"bad.py": 'cursor.execute(f"SELECT * FROM {table}")'}
        passed, findings = SecurityAudit.check_sql_injection(files)
        assert passed is False
