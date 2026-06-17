"""Shared backend module: DB access, HTTP helpers, error mapping.

Single source of truth imported by every service Lambda (delivered as a Lambda
layer at runtime). Service-specific code (models, repositories, routing) lives in
each service folder; cross-cutting concerns live here so they are defined once.
"""
