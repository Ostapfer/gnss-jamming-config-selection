# Proof of concept: precedents and limits of Docker resource emulation

Verified on 26 October 2026. This is an independent literature check, not an execution of a software prototype. The runtime, models and containers were unchanged. The complete metadata/claim map is in `citation_ledger.json`; BibTeX is in `verified_references.bib`.

## Response to the question

**Scientific precedents exist**, including closely related work on UAV security. They support controlled resource constraints, not an automatic equivalence between a CPU fraction on a Mac and a particular UAV processor. Such an equivalence for our GNSS detector was not established among the checked sources.

The DIRECT level means a direct precedent for the specified technique, **not** validation of our data, numerical limits or hardware fidelity.

| ID | What the primary source confirms | Applicability limit |
|---|---|---|
| CHEN2026 | Abstract-verified UAV/MAVLink embedded-like container under 0.5 CPU / 100 MiB and bounded logging. Host traffic / Pi 4 details are INDEXED_TEXT_ONLY; see verification_notes.md | Closely related resource/security precedent. Does not confirm our producer design or equivalence to a specific UAV CPU |
| FOGIFY2020 | Docker/cgroups and Compose for resource emulation; comparison of specific deployments with physical devices | Supports resource shaping. Its validation does not transfer to our Mac/GNSS workload |
| IOTIER2021 | Container CPU/memory shaping, microbenchmark validation and a separate controller/runtime | Frequency mapping is heuristic. The paper's reservation claim does not mean that ordinary CPU quota reserves resources for us |
| TRIHINAS2022 | CPU capping and inference measurements on a server and a real Pi 4 | Supports paired physical/controlled-resource evaluation; power/latency mapping is device-dependent |
| KNOCHE2018 | Docker/native performance replication on a physical Raspberry Pi | Macrobenchmark reproducibility depends on peripherals; container portability does not imply hardware equivalence |
| GUPTA2025 | Docker measurements on physical Pi devices, including AI workloads; short poster paper | An alternative validation route, not Pi emulation on a desktop. The full PDF was not checked |
| GEM52011 | CPU/ISA/memory-system architectural modeling with different speed/accuracy tradeoffs | An alternative for a specific processor model, requiring target configuration/validation. Not a ready-made prediction for our SBC |
| AIRSIM2018 | UAV physics/visual simulation and HITL support | An alternative for flight/autopilot integration; not proof of guest CPU performance |

Direct URLs, DOIs, authors and locators are in the ledger; its `verification_scope` distinguishes full papers, abstracts and indexed publisher text. Do not present an unavailable PDF as fully read.

## Recommendation for this decision

1. Describe the current stage as a **container-enforced CPU/RAM sensitivity study on Linux ARM64 hosted by a Mac**. Do not call it “emulation of a UAV processor.”
2. Use separate producer/controller and detector resource domains, bounded instrumentation and a failure journal. This is our own controlled design, supported by precedents but requiring our integration test.
3. A claim about a specific onboard platform requires checking the same workloads on the target hardware or using a validated target-specific architectural model. Limiting CPU and memory alone does not create such calibration.
4. There is no need to replace the current small experiment with a full Fogify/IOTier/AirSim stack. Cite methodological precedents; do not claim to have used their software.

## Article handoff

Permitted and prohibited formulations are in `ARTICLE_HANDOFF.md` and the ledger's `article_claim_map`. The manuscript should cite a source beside the specific technique and preserve the distinction between precedent and evidence from our experiment. Prior work does not establish the scientific novelty of our entire method.

## Search and negative findings

Queries: `Fogify Docker cgroups CPU RAM emulation`; `IOTier virtual testbed CPU quota`; `UAV Docker CPU quota emulation`; `Raspberry Pi Docker replicable performance experiments`; `gem5 simulator CPU models`; `AirSim hardware in the loop`.

An SSRN 2026 preprint on container dependencies was excluded as primary support because it was not peer reviewed, as were generic examples without verified metadata and incompatible wireless-network data. No exact precedent was found among the checked sources for **our** numerical CPU/RAM grid on a Mac as a calibrated UAV processor. This does not prove that no such research exists.

## Gate for returning to methodological review

**METHOD_PRECEDENT_FOUND; TARGET_HARDWARE_EQUIVALENCE_UNSUPPORTED.** Before implementation, the methodological review must check that the manuscript claim is limited to resource sensitivity, input/root and instrumentation blockers are addressed in the design, source-counter/clock controls are declared, and no precedent is presented as our experimental result.
