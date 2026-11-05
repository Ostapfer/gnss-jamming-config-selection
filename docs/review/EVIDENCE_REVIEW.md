# Reassessment of scientific evidence and the design decision

26 October 2026. Reviewed the updated `RESEARCH_PROPOSAL_V2.md`, `docs/evidence/CONTAINER_METHOD_EVIDENCE.md`, `citation_ledger.json`, `verified_references.bib` and `ARTICLE_HANDOFF.md`. This reviews literature evidence and the proposed design. No code was changed and no containers, inference, benchmarks or technical prototypes were run.

## Final scoped verdict

**ACCEPT_FOR_IMPLEMENTATION — option A, container-enforced resource sensitivity.**

The design is sufficiently justified to implement the agreed architecture and perform local acceptance checks. This passes **DESIGN_ACCEPTED_FOR_IMPLEMENTATION**, not **VERIFIED_FOR_MEASUREMENT**. Do not begin the full 60-trial pilot until G2–G6 are closed and the measurement gate is recorded. Requiring a finished runtime for design acceptance would create the circular condition “implementation is forbidden until implementation is complete.”

The agreed scope of 5 configurations × 4 profiles × 3 sessions × 1 trial and the lower bound of approximately 3.356 h for original-rate playback remain unchanged. This is a descriptive resource pilot, not a repeatability study or independent GNSS validation.

## What the evidence supports

1. **Container CPU/RAM ceilings have scientific precedents as a controlled-evaluation method.** The [primary university record for Chen2026](https://research.mpu.edu.mo/zh/publications/mission-preserving-protocol-defense-an-in-situ-mavlink-honeypot-w/), DOI 10.1016/j.comcom.2026.108613, was independently reopened. Its abstract explicitly describes a UAV-security component, a 0.5 CPU/100 MiB containerized setting and ring-buffer/constant-space logging. This establishes a close precedent, not transferability of those numbers to our detector.
2. **Resource shaping through Docker/cgroups is a concrete documented mechanism, not merely a naming analogy.** The original [Fogify paper, university-hosted copy](https://classpages.cselabs.umn.edu/Fall-2021/csci8980-ec/papers/Fogify.pdf), Section V.B, pp. 6–7, was independently read. It describes CPU-quota/RAM restrictions and a separate validation procedure. Its validation results concern its workloads and platforms; they do not calibrate our hardware.
3. **Bounded logging has a close direct precedent** in Chen. Keeping full history in a collector and controlling buffers is our implementation of this principle and still requires local memory/overhead/failure checks.
4. **A producer outside the detector quota is primarily a causal experimental control.** If both share a CPU ceiling, changing the treatment can also change the workload. This requirement follows from controlling variables in our design; it should not be presented as a theorem proved by another paper's abstract. The updated ledger and `docs/evidence/verification_notes.md` label host-generated traffic/Pi4 details as INDEXED_TEXT_ONLY and not_gate_evidence; the accessible Chen abstract alone does not establish those details. Cite the source within its verification_scope.
5. Other ledger entries support alternatives and validation routes with different scopes. Eight unique DOIs and all eight BibTeX keys were structurally checked. This does not claim that all eight full PDFs were independently read: abstract-only and full-text scopes remain distinct in the ledger.

## What the evidence does not establish

- `0.25 CPU on Mac = a named UAV/SBC processor`; CPU frequency/quota does not model the full ISA/cache/memory/I/O/thermal behavior.
- Our CPU/RAM limits are an operational standard or calibrated onboard resource levels.
- One technical trial establishes a reliable latency-tail distribution or a stable Pareto frontier.
- Sources establish our timely detection, generalization, intrinsic model RAM, energy consumption or novelty of the complete method.

Option B can only be a separate target-specific calibration hypothesis with actual validation. Option C is direct hardware evaluation when a device is available. Neither is required for the first pilot, and ordinary Docker limits cannot substitute for them.

## Why the previous design objections are resolved

| Round 1 objection | Accepted clarification in research proposal v2 | Consequence |
|---|---|---|
| Arrival ambiguously means producer send or receiver availability | `accepted_ingress_available` means accepted bounded ingress available to the pipeline; before-send is diagnostic only. The endpoint remains `event_ready − mapped_annotated_onset` | The boundary is now defined; the transport must implement it under G3 |
| Transport/failure conditions lack numeric values | Freeze capacity/drop/backpressure/timeouts/source-validity/evidence-loss policies numerically before measurement; do not exclude slow-detector overflow as source-invalid | The design prevents concealment of treatment failure, although numerical engineering policies remain pending |
| Mandatory admission of all 66 models expands the pilot | Full functional parity is required only for the five selected configurations; broader checks are optional | The agreed scope is preserved |
| Numerical score tolerance could conceal threshold crossings | Tolerance cannot permit changes in crossings, positive decisions, states or events | Frozen detector behavior is an acceptance invariant |
| Conceptual design acceptance and runtime verification are conflated | Two explicit gates have different evidence requirements | Implementation may proceed, but the full pilot is not yet authorized by this review |

An editorial sentence in option A was also corrected: literature evidence does not “close the three runtime blockers.” It supports a limited methodological precedent; implementation checks must close the blockers before measurement. This review was finalized after rereading the updated proposal and verification notes.

## Mandatory implementation conditions before the measurement gate

**G2:** Configurable input root, hashes/schemas and parity for five configurations through calibration/preprocessing/score/states/events. Do not use a monkeypatched module ROOT as the final input contract. Finite direct-pickle predictions do not replace this check.

**G3:** Different producer/detector cgroup IDs; actual ceilings; verified Linux clock/time namespace; accepted-ingress/receive/start/event-ready traces; a synthetic known-delay/backlog case. A separate producer cgroup does not guarantee the source rate: its validity must also be measured.

**G4:** Bounded detector storage; lifecycle memory after import/loading/calibration and available peak/counters; producer/collector and total-system overhead reported separately. Collector progress must not silently slow the source. The earlier approximately 17 MiB value remains a pre-import snapshot, not a runtime baseline.

**G5:** Record attempts before start; retain startup/timeout/exit/OOM/incomplete/partial-trace cases; inspect before cleanup; exit 137 alone does not prove OOM. Detector-induced drops/backpressure remain in scope. Evidence loss cannot create a PASS.

**G6:** Freeze image/source/input/model/adapter/version, the 60-pair manifest/order, buffer/drop/timeout policies, threads, scope and aggregation. Use a same-image Linux reference. Reference 1536 MiB versus restricted 512 MiB is not a pure CPU contrast; compare 1/0.5/0.25 CPU at 512 MiB for that purpose. Repeated containers do not increase recording/episode statistical independence.

This review does not implement these conditions. All three runtime P1 findings in `DESIGN_AUDIT.md` remain open **for measurement**, but their remedies are sufficiently specific and do not constitute unresolved design P1 findings.

## Implementation and manuscript handoff

Implementation receives accepted design A with the gates above, not permission to execute 60 trials on the unchanged readiness image. Before `VERIFIED_FOR_MEASUREMENT`, only implementation and local engineering acceptance checks under a separate work assignment may proceed.

The manuscript may justify the controlled resource-sensitivity method using the sources and describe the planned pilot, but pilot results do not yet exist at this review stage. Sources provide method precedents, not proof of novelty or hardware equivalence. Another study's memory/latency/accuracy numbers are not our results. Both no bottleneck at 1 Hz and failure under some profiles are valid future pilot outcomes.
