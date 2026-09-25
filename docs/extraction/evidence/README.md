# Evidence probes

These scripts test predecessor behavior. They only read the predecessor repositories; all writes go to temporary directories. The `.out.txt` files are the output captured on 2026-09-24.

| Script | Run from | Predecessor |
|---|---|---|
| `probe_clicksavvy_infrastructure.py` | anywhere | `C:\Users\mohdo\Downloads\ClickSavvy-SEO-main\ClickSavvy-SEO-main\infrastructure` (needs `bs4`) |
| `probe_metanous_human_writing.py` | `C:\Users\mohdo\Documents\Metanous\content-engine` | Metanous engine + work item W-20260916-001 |
| `probe_metanous_gate_bypasses.py` | `C:\Users\mohdo\Documents\Metanous\content-engine` | Metanous engine test fixtures |
| `metanous_test_suite.out.txt` | `C:\Users\mohdo\Documents\Metanous`: `python -m unittest discover -s content-engine/tests` | Metanous test suite (71 pass) |

Several of these failure modes become regression tests in CraftyProse (architecture proposal §17).
