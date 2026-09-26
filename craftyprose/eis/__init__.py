"""EIS, the Editorial Intelligence System: the governed context and judgment layer.

It holds what is true about the brand, what may be said, who the content speaks
to and as whom, and what "good" and "defective" mean (architecture §3). It
doesn't move work; the orchestrator does. It doesn't write; roles do.

* ``workspace``: the brand workspace (context and permission)
* ``contradictions``: brand rules that conflict with each other
* ``guardrails``: brand rules compiled into deterministic checks
* ``context``: the declared EIS slice each role receives
* ``standards``: the failure-pattern library and editorial principles
* ``provenance``: where a text sample came from and what rights we hold
"""
