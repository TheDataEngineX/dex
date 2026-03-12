"""CareerDEX Notification System.

Sends notifications via Slack and GitHub instead of email.
Uses loguru for structured logging.

Raises ``NotificationError`` on failure — notifications are never
silently skipped.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

import requests
from loguru import logger

from .exceptions import NotificationError

logger.enable("careerdex")


class SlackNotifier:
    """Sends notifications to Slack."""

    def __init__(self, webhook_url: str, channel: str = "#careerdex-alerts"):
        """Initialize Slack notifier.

        Args:
            webhook_url: Slack incoming webhook URL
            channel: Target Slack channel
        """
        self.webhook_url = webhook_url
        self.channel = channel
        logger.info("initialized Slack notifier for channel=%s", channel)

    def send_message(
        self,
        title: str,
        message: str,
        status: str = "info",
        extra_fields: Mapping[str, Any] | None = None,
    ) -> bool:
        """Send formatted message to Slack.

        Args:
            title: Message title
            message: Message body
            status: Status level (info, success, warning, error)
            extra_fields: Additional fields to include

        Returns:
            True if sent successfully

        Raises:
            NotificationError: If the Slack API call fails.
        """
        # Color mapping for status
        colors = {
            "info": "#0099FF",
            "success": "#00CC44",
            "warning": "#FFAA00",
            "error": "#FF0000",
        }

        payload = {
            "channel": self.channel,
            "attachments": [
                {
                    "color": colors.get(status, "#0099FF"),
                    "title": title,
                    "text": message,
                    "ts": int(datetime.now(tz=UTC).timestamp()),
                }
            ],
        }

        # Add extra fields if provided
        if extra_fields:
            fields = []
            for key, value in extra_fields.items():
                fields.append(
                    {
                        "title": key,
                        "value": str(value),
                        "short": True,
                    }
                )
            payload["attachments"][0]["fields"] = fields

        try:
            response = requests.post(self.webhook_url, json=payload)
            response.raise_for_status()
            logger.info("Slack notification sent: title=%s", title)
            return True
        except requests.exceptions.RequestException as exc:
            msg = f"Failed to send Slack notification: {exc}"
            logger.error(msg)
            raise NotificationError(msg) from exc


class GitHubStatusNotifier:
    """Updates GitHub commit status and creates check runs."""

    def __init__(self, repo: str, token: str, context: str = "careerdex/pipeline"):
        """Initialize GitHub notifier.

        Args:
            repo: Repository in format "owner/repo"
            token: GitHub personal access token
            context: Status context name
        """
        self.repo = repo
        self.token = token
        self.context = context
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        }
        logger.info("initialized GitHub notifier for repo=%s", repo)

    def update_status(
        self, sha: str, state: str, description: str, target_url: str | None = None
    ) -> bool:
        """Update commit status on GitHub.

        Args:
            sha: Commit SHA
            state: Status state (pending, success, failure, error)
            description: Status description
            target_url: URL for the status

        Returns:
            True if successful

        Raises:
            NotificationError: If the GitHub API call fails.
        """
        url = f"{self.base_url}/repos/{self.repo}/statuses/{sha}"

        payload = {
            "state": state,
            "description": description,
            "context": self.context,
        }

        if target_url:
            payload["target_url"] = target_url

        try:
            response = requests.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            logger.info("GitHub status updated: state=%s desc=%s", state, description)
            return True
        except requests.exceptions.RequestException as exc:
            msg = f"Failed to update GitHub status: {exc}"
            logger.error(msg)
            raise NotificationError(msg) from exc

    def create_deployment_status(
        self, deployment_id: int, state: str, description: str, environment: str = "production"
    ) -> bool:
        """Create deployment status on GitHub.

        Args:
            deployment_id: GitHub deployment ID
            state: Status state (pending, success, failure, error)
            description: Status description
            environment: Deployment environment

        Returns:
            True if successful

        Raises:
            NotificationError: If the GitHub API call fails.
        """
        url = f"{self.base_url}/repos/{self.repo}/deployments/{deployment_id}/statuses"

        payload = {
            "state": state,
            "description": description,
            "environment": environment,
        }

        try:
            response = requests.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            logger.info("GitHub deployment status created: state=%s", state)
            return True
        except requests.exceptions.RequestException as exc:
            msg = f"Failed to create GitHub deployment status: {exc}"
            logger.error(msg)
            raise NotificationError(msg) from exc


class PipelineNotifier:
    """Combined notifier for Slack and GitHub."""

    def __init__(self, slack_webhook: str, github_repo: str, github_token: str):
        """Initialize pipeline notifier with Slack and GitHub.

        Args:
            slack_webhook: Slack webhook URL
            github_repo: GitHub repo in format "owner/repo"
            github_token: GitHub personal access token
        """
        self.slack = SlackNotifier(slack_webhook)
        self.github = GitHubStatusNotifier(github_repo, github_token)
        logger.info("initialized PipelineNotifier with Slack and GitHub")

    def notify_pipeline_start(self, execution_id: str, timestamp: datetime) -> bool:
        """Notify pipeline start."""
        logger.info("pipeline started: execution_id=%s", execution_id)

        return self.slack.send_message(
            title="CareerDEX Pipeline Started",
            message=f"Job ingestion pipeline started (Execution ID: {execution_id})",
            status="info",
            extra_fields={
                "Execution ID": execution_id,
                "Timestamp": timestamp.isoformat(),
            },
        )

    def notify_pipeline_success(
        self, execution_id: str, job_count: int, quality_score: float, duration_seconds: float
    ) -> bool:
        """Notify pipeline success."""
        logger.info("pipeline succeeded: execution_id=%s", execution_id)

        return self.slack.send_message(
            title="✓ CareerDEX Pipeline Succeeded",
            message="Job ingestion completed successfully",
            status="success",
            extra_fields={
                "Jobs Processed": f"{job_count:,}",
                "Quality Score": f"{quality_score:.2%}",
                "Duration": f"{duration_seconds:.1f}s",
                "Execution ID": execution_id,
            },
        )

    def notify_pipeline_failure(self, execution_id: str, error: str, task_name: str) -> bool:
        """Notify pipeline failure."""
        logger.error("pipeline failed: execution_id=%s task=%s", execution_id, task_name)

        return self.slack.send_message(
            title="✗ CareerDEX Pipeline Failed",
            message=f"Pipeline failed at task: {task_name}",
            status="error",
            extra_fields={
                "Task": task_name,
                "Error": error,
                "Execution ID": execution_id,
            },
        )

    def notify_data_quality_issue(
        self, quality_score: float, threshold: float, issues: list[str]
    ) -> bool:
        """Notify data quality issues."""
        logger.warning("data quality issue: score=%.2f threshold=%.2f", quality_score, threshold)

        return self.slack.send_message(
            title="⚠ Data Quality Issue",
            message=f"Quality score {quality_score:.2%} below threshold {threshold:.2%}",
            status="warning",
            extra_fields={
                "Quality Score": f"{quality_score:.2%}",
                "Threshold": f"{threshold:.2%}",
                "Issues": " | ".join(issues[:3]),
            },
        )
