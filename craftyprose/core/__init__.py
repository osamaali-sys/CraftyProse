"""Core engine: work-item state, artifacts, gates, findings, routing and budgets.

The core knows nothing about brands, content types, prompts or providers. Those
plug in through stage definitions (``core.stages``) and the LLM adapter
(``craftyprose.runtime``).
"""
