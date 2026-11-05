# Sources for the article — 26 October 2026

The cards report source-verification findings. Access completeness is part of each claim; the manuscript must not treat a snippet or abstract as full-text evidence. Links lead to primary sources or author manuscripts. The complete machine-readable register is ARTICLE_SOURCES.json.

## SCHROEDER2006

[Open Versus Closed: A Cautionary Tale](https://www.usenix.org/legacy/event/nsdi06/tech/full_papers/schroeder/schroeder_html/)

Year: 2006; DOI: not established / not applicable; access: **FULL_TEXT**.

Permitted scope: Closed-loop load generation underestimates response time compared with an open-loop model (METHOD_ANALOGY).

Does not establish: Specific numerical queue capacities or GNSS-detector timeouts.

Verification: POC_A_UK.md:A1 (USENIX NSDI 2006, Sections 1, 2, 4.1, 4.2, 5.1).

## KARIMOV2018

[Benchmarking Distributed Stream Data Processing Systems](https://arxiv.org/html/1802.08496v2)

Year: 2018; DOI: 10.1109/ICDE.2018.00169; access: **FULL_TEXT_ARXIV_IEEE_418_UNAVAILABLE**.

Permitted scope: Stream workload/latency measurement methodology supports separating source time, ingress and processing, and accounting for measurement/load-generation coupling; our cgroup architecture is an adaptation.

Does not establish: That this paper validates our GNSS implementation, exact queue/timeouts or the unverified page1521 locator.

Verification: POC_A_UK.md / A1; use section-level pointer III-B/III-C only; page1521 from supplement is rejected.

## SYMEONIDES2020

[Fogify: A Fog Computing Emulation Framework](https://www.cs.ucy.ac.cy/mdd/docs/2020-SEC-Fogify.pdf)

Year: 2020; DOI: 10.1109/SEC50012.2020.00011; access: **FULL_TEXT**.

Permitted scope: Container CPU/RAM shaping is a research testbed method; target fidelity needs separate hardware/workload validation.

Does not establish: Our Mac quotas equal a UAV CPU; detailed Fogify formulas or numeric fidelity claims are excluded from this Article handoff pending passage-level check.

Verification: POC_A_SUPPLEMENT_UK.md / A2.

## CHEN2026

[Mission-preserving protocol defense: An in-situ MAVLink honeypot with benchmark-calibrated thresholds and constant-space logging](https://research.mpu.edu.mo/zh/publications/mission-preserving-protocol-defense-an-in-situ-mavlink-honeypot-w/)

Year: 2026; DOI: 10.1016/j.comcom.2026.108613; access: **ABSTRACT_ONLY**.

Permitted scope: The abstract reports constrained-container evaluation and constant-space/ring-buffer logging.

Does not establish: External producer/collector architecture, our RAM values, hardware equivalence or uninspected implementation details.

Verification: POC_A_SUPPLEMENT_UK.md / A3.

## TATBUL2018

[Precision and Recall for Time Series](https://ar5iv.labs.arxiv.org/html/1803.03639)

Year: 2018; DOI: not established / not applicable; access: **FULL_TEXT**.

Permitted scope: Event/range-based evaluation of time-series anomalies that accounts for positional bias and duration (METHOD_ANALOGY).

Does not establish: The constants 30 s, confirm=2, recovery=2, gap=1.5 s or the X/T/Y grid.

Verification: POC_B_UK.md:B2 (NeurIPS 31 abstract + ar5iv Sections 1–5).

## LAU2021

[A Novel Link Failure Detection and Switching Algorithm for Dissimilar Redundant UAV Communication](https://www.mdpi.com/2504-446X/5/2/48)

Year: 2021; DOI: 10.3390/drones5020048; access: **FULL_TEXT**.

Permitted scope: Detection of a lost UAV message stream using a countdown timer (heartbeat timeout) as an indicator of link/telemetry loss (METHOD_ANALOGY).

Does not establish: GNSS-jamming ground truth or an established value for our watchdog threshold; this is a communications-link-health analogy.

Verification: POC_B_UK.md:B2 (MDPI Drones 5(2):48, Sections 2.1–2.2).

## THULIN2017

[Exact confidence intervals and hypothesis tests for parameters of discrete distributions](https://ar5iv.labs.arxiv.org/html/1412.0442)

Year: 2017; DOI: 10.3150/15-BEJ750; access: **FULL_TEXT**.

Permitted scope: Exact one-sided Clopper–Pearson and Garwood confidence bounds are valid for small samples without an N>=5 requirement; statistical proof of X=1 or Y=0 is unattainable with finite data (DIRECT_PRECEDENT).

Does not establish: That the current sessions meet binomial/Poisson sampling assumptions, a minimumN>=5rule, or simultaneous95%guarantees for all scenarios.

Verification: POC_B_UK.md:B3 (ar5iv Section 1, Equation 1).

## BROWN2001

[Title not yet confirmed](https://doi.org/10.1214/ss/1009213286)

Year: 2001; DOI: 10.1214/ss/1009213286; access: **ABSTRACT_ONLY**.

Permitted scope: General statistical context for interval estimation of a binomial proportion.

Does not establish: An N>=5 rule or session independence in our experiments.

Verification: POC_B_UK.md:B3 (Statist. Sci. 16(2):101–133).

## NIST_HANDBOOK

[NIST/SEMATECH e-Handbook of Statistical Methods (Sections 7.2.4.1, 8.4.5.1)](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm)

Year: unknown; DOI: not established / not applicable; access: **FULL_TEXT**.

Permitted scope: Official formulas for binomial bounds and an upper Poisson rate bound through the chi-square distribution under an HPP assumption (OFFICIAL_DOCS).

Does not establish: Statistical validity without binomial/HPP assumptions or independent evidence; the CI engine is not implemented.

Verification: POC_B_UK.md:B3 (Sections 7.2.4.1 and 8.4.5.1).

## KAPOOR2023

[Leakage and the reproducibility crisis in machine-learning-based science](https://www.cell.com/patterns/fulltext/S2666-3899(23)00159-9)

Year: 2023; DOI: 10.1016/j.patter.2023.100804; access: **FULL_TEXT**.

Permitted scope: Classification of temporal leakage [L3.1] and session/group dependence [L3.2], and the absence of an advantage of complex ML models over simple baselines after leakage removal (DIRECT_PRECEDENT).

Does not establish: Cross-session generalization of models trained on a single attack recording.

Verification: POC_C_UK.md:C1 (Summary, Introduction, Results: Taxonomy [L1.2], [L1.3], [L3.1], [L3.2]).

## ARP2022

[Dos and Don'ts of Machine Learning in Computer Security](https://www.usenix.org/conference/usenixsecurity22/presentation/arp)

Year: 2022; DOI: not established / not applicable; access: **ABSTRACT_ONLY**.

Permitted scope: The methodological requirement to compare ML models with simple baseline rules and avoid data leakage in security tasks.

Does not establish: Exact P1–P10 pitfall numbers without textual verification of the PDF.

Verification: POC_C_UK.md:C1 (USENIX page + structure of sec22-arp.pdf without a text layer).

## KAUFMAN2012

[Leakage in data mining: Formulation, detection, and avoidance](https://doi.org/10.1145/2382577.2382579)

Year: 2012; DOI: 10.1145/2382577.2382579; access: **METADATA_ONLY_FROM_KAPOOR2023_REF10**.

Permitted scope: An additional bibliographic reference on the concept of data leakage.

Does not establish: Specific quotations or theorems from the full ACM article.

Verification: POC_C_UK.md:C1 (confirmed from Kapoor & Narayanan reference list, Ref. 10).

## SORMAYLI2025

[Real-Time jamming detection using windowing and hybrid machine learning models for pre-saturation alerts](https://www.nature.com/articles/s41598-025-10567-0)

Year: 2025; DOI: 10.1038/s41598-025-10567-0; access: **FULL_TEXT**.

Permitted scope: Receiver-telemetry jamming detection, feature/normalization/windowing examples and a controlled transmitter/receiver setup are methodological analogies.

Does not establish: Cross-receiver feature equivalence, raw development receiver/driver provenance, or the study-specific 30 s calibration, 25-observation minimum, two confirmations and 1.5 s gap constants.

Verification: POC_C_SUPPLEMENT_UK.md / C2-C3; POC_CITATION_CORRECTION_UK.md.

## PX4_SENSORGPS_V114

[SensorGps | PX4 User Guide v1.14](https://docs.px4.io/v1.14/en/msg_docs/SensorGps.html)

Year: unknown; DOI: not established / not applicable; access: **FULL_TEXT**.

Permitted scope: The PX4 schema defines eph as horizontal accuracy in metres separately from hdop and lists receiver noise/jamming diagnostics.

Does not establish: Actual receiver/driver/firmware identity in our raw recordings, Gaussian1sigma meaning, or universal cross-device comparability.

Verification: POC_C_SUPPLEMENT_UK.md / C2.

