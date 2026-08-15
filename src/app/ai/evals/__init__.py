"""Offline measurement of AI behaviour. Not on the request path.

May import any layer; nothing imports it. That is the one documented exception to the
dependency direction, and it holds because evals never runs in a request.

An eval asks "did this change make the system better?" A test asks "does this code
still work?" They do not replace each other.

Conventions: evals/AGENTS.md.
"""
