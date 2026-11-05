# Real cells (handout section 4, step 11)

Each request of the final set (`cells/requests/`) is answered by a response in `cells/responses/<cell>.json` (overview, Appendix A). A response is used only if its status is pass, its Liberty file holds exactly one cell group with the requested name and pins, and its function equals the requested truth table (`src/responses.py`).

| Cell | Estimated area (um2) | Real area (um2) | Status | Problems |
|---|---|---|---|---|
| `dd2_g5__f000b_1` | 8.7584 | - | no response | - |
| `dd2_g5__f0ee0_1` | 13.7632 | - | no response | - |
| `dd2_g5__f00eb_1` | 13.7632 | - | no response | - |
| `dd2_g5__f009f_1` | 12.5120 | - | no response | - |
| `dd2_g5__feee8_1` | 11.2608 | - | no response | - |
| `dd2_g5__f008e_1` | 12.5120 | - | no response | - |
| `dd2_g5__f00be_1` | 13.7632 | - | no response | - |
| `dd2_g5__fa888_1` | 8.7584 | - | no response | - |
| `dd2_g5__f006f_1` | 12.5120 | - | no response | - |

No response has been accepted yet, so Table 5 with real areas, the real-area curve and the real-area 30% experiment are not measured. They are produced by `python src/run_step.py 11` as soon as the responses are in `cells/responses/`.
