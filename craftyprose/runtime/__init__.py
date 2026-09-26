"""LLM runtime: the adapter contract, replay for tests, pricing and metering.

Adapters (ADR-012): ``ReplayLLM`` (tests; here), ``AnthropicLLM`` (production;
milestone M8) and ``ManualLLM`` (driven mode; milestone M4). Every adapter is
wrapped by ``MeteredLLM`` so each call is measured (ADR-016).
"""
