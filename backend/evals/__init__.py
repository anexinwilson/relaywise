"""Evaluation suite.

Runs on a developer machine or in CI — never in Lambda. The LangSmith key
therefore belongs in `backend/.env.local` and in CI secrets, not in AWS
Secrets Manager.
"""
