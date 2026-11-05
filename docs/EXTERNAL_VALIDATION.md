# External evidence and portability boundaries

The final article uses two IGASPIN static ZED-F9P recordings: one chirp-jamming and one expected-clean. They originate separately from the development source. They do not establish broad independent GNSS detection performance: physical interference onset/uncertainty/end, clean exposure and RF epoch/band semantics remain unresolved.

The separate offline diagnostic covers 48 unchanged models, f1–f4, 288 ML configurations plus two c2 rules per ordinal RF position. The primary group is 98 configurations per position. These counts are model settings on the same observations, not independent trials. The Docker extension measures only five selected variants and must not inherit results for all 98.

All 80 resource workloads completed; 79 met source-schedule timing. The discarded timing attempt remains in trial tables. New alarms after the conditional reference, carry-in alarms and absence of a new event are distinguished. DT confirms at approximately 11 s; the other four selected variants have no fresh post-reference event. Exact values and limits are in FINAL_RESULTS.md.

The byte-identical offline adapter and diagnostic replay function are supplied under validation/igaspin/. Data-dependent preparation is supported with separately obtained exact raw files. The original machine-specific 80-trial controller and private trained/trace bundle are not a turnkey portable release. Archived aggregate reconstruction is supported without those dependencies. Relocated execution requires a new reviewed protocol and cannot rewrite the historical freeze.

Physical deadline and operational FAR are NOT EVALUABLE on the available provider-reference metadata. Repetition, RF positions and similar source fields do not add independent campaigns, establish a target-UAV processor or validate a universal winner.
