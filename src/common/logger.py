"""
Structured logging configuration for the Football Virtual Waiting Room.

Uses AWS Lambda Powertools Logger for consistent, structured JSON logging
across all Lambda functions.
"""

from aws_lambda_powertools import Logger

# Shared logger instance — imported by all Lambda functions.
# The service name is set to a default; each Lambda can override via
# the ``POWERTOOLS_SERVICE_NAME`` environment variable.
logger: Logger = Logger(
    service="football-waiting-room",
    log_uncaught_exceptions=True,
)
