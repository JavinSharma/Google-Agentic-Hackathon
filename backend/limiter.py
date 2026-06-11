"""Shared rate-limiter instance.

Import ``limiter`` into route modules and ``main.py`` to attach middleware /
decorators without creating circular import issues.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

# Key function: rate-limit per client IP address.
# Swap `get_remote_address` for a custom callable if you want to key on user_id.
limiter = Limiter(key_func=get_remote_address)
