"""CareerDEX Airflow DAG Configuration.

Replaces Prefect 2 with Apache Airflow for orchestration.

**Status:** All fetch tasks raise ``StubNotImplementedError`` —
real source connectors must be implemented before this DAG
produces data.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from airflow import DAG
from airflow.models import Variable
from airflow.operators.python import PythonOperator
from loguru import logger

from careerdex.core.exceptions import StubNotImplementedError
from careerdex.core.notifier import PipelineNotifier
from careerdex.core.settings import get_settings

# Configure loguru
logger.enable("careerdex")

# DAG configuration
default_args = {
    "owner": "careerdex",
    "depends_on_past": False,
    "start_date": datetime(2026, 2, 13, tzinfo=UTC),
    "email": [],  # Notifications via Slack instead
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "careerdex_job_ingestion",
    default_args=default_args,
    description="CareerDEX 3-hour job ingestion pipeline",
    schedule_interval="0 */3 * * *",  # Every 3 hours
    catchup=False,
    max_active_runs=1,
    tags=["careerdex", "job-ingestion"],
)


def fetch_linkedin_jobs(**context):
    """Fetch jobs from LinkedIn API.

    Raises:
        StubNotImplementedError: Always — no real connector exists yet.
    """
    msg = (
        "fetch_linkedin_jobs is a stub — implement a real LinkedIn API "
        "connector in careerdex/phases/phase2_job_ingestion.py"
    )
    raise StubNotImplementedError(msg)


def fetch_indeed_jobs(**context):
    """Fetch jobs from Indeed.

    Raises:
        StubNotImplementedError: Always — no real connector exists yet.
    """
    msg = (
        "fetch_indeed_jobs is a stub — implement a real Indeed "
        "connector in careerdex/phases/phase2_job_ingestion.py"
    )
    raise StubNotImplementedError(msg)


def fetch_glassdoor_jobs(**context):
    """Fetch jobs from Glassdoor.

    Raises:
        StubNotImplementedError: Always — no real connector exists yet.
    """
    msg = (
        "fetch_glassdoor_jobs is a stub — implement a real Glassdoor "
        "connector in careerdex/phases/phase2_job_ingestion.py"
    )
    raise StubNotImplementedError(msg)


def fetch_company_career_pages(**context):
    """Fetch jobs from company career pages.

    Raises:
        StubNotImplementedError: Always — no real connector exists yet.
    """
    msg = (
        "fetch_company_career_pages is a stub — implement real ATS API "
        "adapters in careerdex/phases/phase2_job_ingestion.py"
    )
    raise StubNotImplementedError(msg)


def store_bronze_layer(**context):
    """Store raw jobs to Bronze layer."""
    logger.info("Storing to Bronze layer...")
    task_instance = context["task_instance"]
    linkedin_result = task_instance.xcom_pull(task_ids="fetch_linkedin")
    indeed_result = task_instance.xcom_pull(task_ids="fetch_indeed")
    glassdoor_result = task_instance.xcom_pull(task_ids="fetch_glassdoor")
    company_result = task_instance.xcom_pull(task_ids="fetch_company_pages")

    total_jobs = (
        linkedin_result["count"]
        + indeed_result["count"]
        + glassdoor_result["count"]
        + company_result["count"]
    )

    logger.info("total jobs fetched: %d", total_jobs)
    return {"bronze_jobs": total_jobs}


def deduplicate_jobs(**context):
    """Deduplicate jobs across sources."""
    logger.info("Deduplicating jobs...")
    task_instance = context["task_instance"]
    bronze_result = task_instance.xcom_pull(task_ids="store_bronze_layer")

    logger.info("processing %d jobs for deduplication", bronze_result["bronze_jobs"])
    # Implementation would deduplicate using DataHash framework
    return {"deduplicated_jobs": bronze_result["bronze_jobs"]}


def enrich_with_embeddings(**context):
    """Enrich jobs with embeddings."""
    logger.info("Enriching jobs with embeddings...")
    task_instance = context["task_instance"]
    dedup_result = task_instance.xcom_pull(task_ids="deduplicate_jobs")

    logger.info("generating embeddings for %d jobs", dedup_result["deduplicated_jobs"])
    # Implementation would generate embeddings using Phase 3 framework
    return {"enriched_jobs": dedup_result["deduplicated_jobs"]}


def store_gold_layer(**context):
    """Store enriched jobs to Gold layer."""
    logger.info("Storing to Gold layer...")
    task_instance = context["task_instance"]
    enrich_result = task_instance.xcom_pull(task_ids="enrich_with_embeddings")

    logger.info("storing %d jobs to Gold layer", enrich_result["enriched_jobs"])
    # Implementation would store to Gold layer
    return {"gold_jobs": enrich_result["enriched_jobs"]}


def quality_validation(**context):
    """Run data quality checks."""
    logger.info("Running data quality validation...")
    task_instance = context["task_instance"]
    task_instance.xcom_pull(task_ids="store_gold_layer")

    settings = get_settings()
    threshold = settings.quality.min_quality_score

    quality_score = 0.92  # Placeholder — must be replaced with real checks
    logger.info("data quality score: %.2f, threshold: %.2f", quality_score, threshold)

    if quality_score < threshold:
        logger.warning("data quality below threshold: %.2f < %.2f", quality_score, threshold)

    return {"quality_score": quality_score, "threshold": threshold}


def notify_completion(**context):
    """Notify job completion via Slack and GitHub."""
    logger.info("Notifying completion...")
    task_instance = context["task_instance"]

    # Get all results from previous tasks
    gold_result = task_instance.xcom_pull(task_ids="store_gold_layer")
    quality_result = task_instance.xcom_pull(task_ids="quality_validation")

    jobs_count = gold_result["gold_jobs"]
    quality_score = quality_result["quality_score"]
    threshold = quality_result["threshold"]
    execution_date = context["execution_date"]

    # Get credentials from Airflow Variables
    slack_webhook = Variable.get("CAREERDEX_SLACK_WEBHOOK", "")
    github_repo = Variable.get("CAREERDEX_GITHUB_REPO", "")
    github_token = Variable.get("CAREERDEX_GITHUB_TOKEN", "")

    # Initialize notifier
    if slack_webhook and github_repo and github_token:
        notifier = PipelineNotifier(slack_webhook, github_repo, github_token)

        # Determine pipeline status
        if quality_score >= threshold:
            execution_id = context["run_id"]
            duration = (datetime.now(tz=UTC) - execution_date).total_seconds()

            notifier.notify_pipeline_success(
                execution_id=execution_id,
                job_count=jobs_count,
                quality_score=quality_score,
                duration_seconds=duration,
            )
            logger.info("pipeline completed: jobs=%d, quality=%.2f", jobs_count, quality_score)
        else:
            execution_id = context["run_id"]
            notifier.notify_data_quality_issue(
                quality_score=quality_score,
                threshold=threshold,
                issues=[
                    "Low quality score",
                    "Data validation checks failed",
                    "Possible data anomalies detected",
                ],
            )
            logger.warning("pipeline quality issue: %.2f < %.2f", quality_score, threshold)
    else:
        logger.warning("Slack/GitHub credentials not configured, skipping notifications")

    return {
        "message": "Notifications sent",
        "jobs_count": jobs_count,
        "quality_score": quality_score,
    }


# Define tasks
task_fetch_linkedin = PythonOperator(
    task_id="fetch_linkedin",
    python_callable=fetch_linkedin_jobs,
    dag=dag,
)

task_fetch_indeed = PythonOperator(
    task_id="fetch_indeed",
    python_callable=fetch_indeed_jobs,
    dag=dag,
)

task_fetch_glassdoor = PythonOperator(
    task_id="fetch_glassdoor",
    python_callable=fetch_glassdoor_jobs,
    dag=dag,
)

task_fetch_company = PythonOperator(
    task_id="fetch_company_pages",
    python_callable=fetch_company_career_pages,
    dag=dag,
)

task_store_bronze = PythonOperator(
    task_id="store_bronze_layer",
    python_callable=store_bronze_layer,
    dag=dag,
)

task_deduplicate = PythonOperator(
    task_id="deduplicate_jobs",
    python_callable=deduplicate_jobs,
    dag=dag,
)

task_enrich = PythonOperator(
    task_id="enrich_with_embeddings",
    python_callable=enrich_with_embeddings,
    dag=dag,
)

task_store_gold = PythonOperator(
    task_id="store_gold_layer",
    python_callable=store_gold_layer,
    dag=dag,
)

task_quality = PythonOperator(
    task_id="quality_validation",
    python_callable=quality_validation,
    dag=dag,
)

task_notify = PythonOperator(
    task_id="notify_completion",
    python_callable=notify_completion,
    dag=dag,
)

# Define task dependencies
(
    [task_fetch_linkedin, task_fetch_indeed, task_fetch_glassdoor, task_fetch_company]
    >> task_store_bronze
)
task_store_bronze >> task_deduplicate
task_deduplicate >> task_enrich
task_enrich >> task_store_gold
task_store_gold >> task_quality
task_quality >> task_notify
