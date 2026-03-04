"""AWS config shared by cashflow routes."""

from __future__ import annotations

import os

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

