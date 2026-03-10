"""Shared slowapi rate limiter instance.

Defined in its own module to prevent circular imports between
api/main.py (which wires app.state.limiter) and auth/routes.py
(which uses the @limiter.limit decorator).
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
