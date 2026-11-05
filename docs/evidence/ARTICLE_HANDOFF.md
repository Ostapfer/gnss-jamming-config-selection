# Article: using the evidence ledger

26 October 2026. Read alongside `citation_ledger.json` and `verified_references.bib`.

| Manuscript claim | Source | Status |
|---|---|---|
| Constrained containers are used for embedded-like UAV security evaluation | CHEN2026 | Supported precedent; not hardware equivalence |
| CPU/RAM resource shaping has precedents in edge/fog emulation | FOGIFY2020, IOTIER2021 | Supported methodological precedent |
| Bounded logging is relevant to a long-running UAV security component | CHEN2026 | Supported design precedent; our implementation still requires verification |
| Container measurements should be supplemented with target-device checks | TRIHINAS2022, KNOCHE2018, GUPTA2025 | Supported evaluation route, not a guaranteed result |
| Architectural simulation and flight-functional simulation are distinct alternatives | GEM52011, AIRSIM2018 | Supported distinction |
| 0.25 CPU on our Mac equals a specific UAV processor | None | DO NOT CLAIM |
| Our 256/512/1024 MiB values are an operational standard | None | DO NOT CLAIM |
| Sources proved our timely detection, minimality or SBC sufficiency | None | DO NOT CLAIM |

Proposed bounded wording: “Evaluation is conducted under controlled container limits on CPU and total memory. This approach has precedents in edge/fog and UAV security testbeds. The results characterize the declared execution environment; correspondence to a specific onboard platform requires separate verification.”

This paragraph is proposed wording, not text already inserted into the manuscript. Do not cite 20 microseconds, 16–19 MiB or another study's accuracy as our results. Do not replace an account of methodological precedents with a claim of novelty or validation of our hardware mapping.

## Revalidation on 26 October 2026

Current supplement: `scholar_revalidation_20261026/ARTICLE_SOURCES.md` and `CORRECTION_PROPOSALS.json`. Fourteen source cards are preserved for nine question groups; access levels and unknowns are explicit. Before citing, check `ERRATA_AND_LIMITS.md`, including the corrected Sormayli title for DOI 10.1038/s41598-025-10567-0. Do not extend source-content claims beyond the cards; do not describe the proposed producer/watchdog as implemented. Do not carry archived bibliographic errors into the final manuscript.
