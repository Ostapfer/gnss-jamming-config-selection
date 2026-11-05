# Completed Docker repeat: analysis checks

The repeat completed all 60 attempts with zero nonzero exits, zero drops and zero cleanup intervention. Exact source/result sequences and raw-latency quantiles were verified against each summary; actual clock identities, time namespaces, distinct cgroups, quotas, memory/swap limits and lifecycle markers were checked.

Raw-trace reconstruction matched all jamming event delays. Every one of the 15 configuration/recording groups had identical scores, states, confirmation/readiness decisions and event sample boundaries across the four profiles. The false-alarm and descriptive front tables were checked separately: 540 scenario ledger rows, 360 empirical PASS and 180 FAIL, all with INSUFFICIENT EVIDENCE.

The exact waiting-queue sweep adds an accepted message at ingress and removes it at processing start, grouping simultaneous deltas. All 60 queues stayed nonnegative, ended empty and reached a transient maximum of one; each integral matched the sum of waits. The historical summary's zero is a post-processing-start observation, not a continuous-time maximum. Original trial summaries were not rewritten.

Processing P95 by recording is distinct from the maximum condition/calibration P95 used for descriptive screening. Startup-inclusive external CPU and post-calibration lifecycle CPU have separate fields. Detector cgroup charge, process RSS, separate driver charge and unavailable kernel peak are not conflated. The reference's 1536 MiB limit is distinguished from the three fixed-512-MiB quota contrasts. No native Mac software-latency budget was imported into Docker.

All published claims remain scoped to one development jamming episode, one spoofing session, one supplementary benign recording and one technical attempt per configuration/profile/session in this repeat. Supervised fits include the replayed episode; the rule threshold was development-selected. SVM's spoofing false event is right-censored. No external validation, true peak-memory guarantee, minimum RAM, target-UAV equivalence or population-level statistical conclusion is established.

Four focused regression fixtures check transient queueing versus post-dequeue observations, backlog integrals and equal timestamps, incomplete/impossible queue histories, and nondominated tradeoffs/equal points. Archived-table reconstruction is checked separately from raw-trace validation. See results/docker_pilot_repeat_20261027/README.md for artifacts and commands.
