"""Agent orchestration, built on LangGraph with langchain-anthropic.

Model choice comes from `Settings.anthropic_model`, never a literal at a call site.
Retrieved documents and tool results are untrusted input.

Conventions: agents/AGENTS.md.
"""
