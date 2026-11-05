# Docker resource-sensitivity pilot: completed repeat

5 frozen configurations, 4 enforced profiles, 3 development recordings and one technical attempt per configuration/profile/recording. All 60 attempts completed with exit 0, no cleanup intervention, no drops and complete raw-trace checks. This analysis performs no new fitting or replay.

## Detection and false alarms

| Configuration | Confirmed execution delay range (s), four profiles | Benign false events per profile | Spoofing false events per profile |
|---|---:|---:|---:|
| RULE_noise_t2_d0.5_c2 | 7.986316–7.995886 | 0 | 0 |
| DT_f3_p2_d0.5_c2 | 1.987394–1.993959 | 0 | 0 |
| KNN_f3_p1_d0.5_c2 | 2.984354–2.992194 | 0 | 0 |
| SVM_f3_p2_d0_c2 | 2.983320–2.986803 | 0 | 1 |
| RF_f3_p3_d0.5_c2 | 2.001243–2.080338 | 0 | 0 |

Each configuration/profile sees the same 445.046782 s benign exposure and 18.983952 s spoofing exposure. Do not add exposure across profiles, models or repeated executions as independent evidence. Zero observed false events does not establish a low real-world false-alarm rate.

SVM produced 1 false jamming event(s) during spoofing in each profile. Observed false-active time was 14.993830 s (78.9816% of that short interval), with 1 right-censored event(s). The arithmetic 189.633855 events/hour is descriptive of this interval, not an established operational rate. Censored durations are not known full event durations.

Raw scores, states, confirmation counts and event sample boundaries were identical across profiles in all 15 configuration/session groups. These are replays of 1 unique development jamming episode, not independent attack trials. ML fitting includes the same episode and cannot establish external generalization. The rule is causal in replay time but was selected after development exploration. See triggering_messages.csv for the trigger-sample delay, accepted-ingress lateness, queue wait and processing-to-event-ready decomposition.

## Processing and memory

Values below are maxima over the three recording-level processing P95 values, in milliseconds. They include calibration in each recording. These are maxima of quantiles, not pooled P95s. Phase-specific quantiles are separate in latency_conditions.csv.

| Algorithm | Reference, 1536 MiB | 1 CPU, 512 MiB | 0.5 CPU, 512 MiB | 0.25 CPU, 512 MiB | Sampled detector cgroup max range (MiB) | Model bytes |
|---|---:|---:|---:|---:|---:|---:|
| RULE | 4.420 | 2.649 | 3.052 | 2.591 | 46.13–46.28 | 79 |
| DT | 7.716 | 20.616 | 7.505 | 8.534 | 103.94–104.07 | 1,856 |
| KNN | 22.363 | 13.638 | 17.861 | 14.281 | 103.59–103.73 | 12,063 |
| SVM | 17.455 | 11.304 | 11.004 | 20.057 | 101.68–102.92 | 2,867 |
| RF | 37.225 | 34.312 | 34.017 | 101.584 | 107.34–107.48 | 241,855 |

RF recording-level processing P95 values were 96.04–101.58 ms at 0.25 CPU and 32.45–34.31 ms at 1 CPU, both with 512 MiB. This tail increase is consistent with observed throttling under a 100 ms quota period, even when average CPU usage is low at a roughly 1 Hz input rate. It is not target-hardware calibration or an isolated causal effect estimate. Other models show scheduling variation rather than uniform monotonic scaling.

One technical attempt per pair and uncontrolled host/VM load do not support statistical speed rankings. The guarded reference additionally changes RAM; fixed-512-MiB comparisons provide the clearest quota contrasts.

Detector cgroup sampled maxima ranged from 46.13 to 107.48 MiB. The separate source/collector had its own 512 MiB budget and sampled maxima of 15.42–16.64 MiB. Paired-sample sums are available in trials.csv. Process RSS is a different accounting quantity; neither value is intrinsic model memory. Kernel memory.peak is unavailable; 100 ms sampled maxima are not true peak guarantees. No lower-memory profile was tested, so 512 MiB is not a measured minimum.

## Startup, queue and CPU scope

Startup below spans before_imports to after_model_load and excludes interpreter/container work before the first marker. Values are medians of three recording-startup measurements, not repeated estimates of the same session. The producer starts the replay clock after model readiness; these startup durations are separate from the annotated-onset detection delay.

| Algorithm | 1 CPU startup (s) | 0.5 CPU startup (s) | 0.25 CPU startup (s) |
|---|---:|---:|---:|
| RULE | 0.324 | 0.600 | 3.916 |
| DT | 1.007 | 2.012 | 14.779 |
| KNN | 0.949 | 2.225 | 13.010 |
| SVM | 0.942 | 1.896 | 14.894 |
| RF | 0.934 | 2.190 | 14.887 |

Post-calibration CPU measured between after_calibration and final lifecycle snapshots ranged from 0.234% to 2.951% of one core. The original external CPU field includes startup/instrumentation and is labelled separately in trials.csv.

The original summaries observed zero waiting messages immediately after processing starts. The derived continuous-time acceptance/start sweep finds a maximum of 1–1 waiting message(s) across trials. Every sweep stays nonnegative, ends at zero, and has an integral equal to the sum of individual waits. The longest queue wait was 296.780 ms. Original summaries were preserved. This roughly 1 Hz workload does not establish stress capacity.

## Functional screening and descriptive Pareto sets

The existing X={0.8, 0.9, 1}, T={3, 5, 10} s and Y={0, 0.5, 1} events/hour grid produces 540 configuration/profile/scenario rows, of which 360 empirically pass. These are not independent experiments. All evidence remains INSUFFICIENT EVIDENCE. Readiness failures stay in the episode denominator; none occurred here. Benign and spoofing false alarms are screened separately. Native mac_experimental latency/model-size budgets are not transferred to Docker. The enforced profiles define tested CPU/RAM allocations; no new latency acceptance threshold is introduced.

Pareto comparison is descriptive within each profile, after empirical functional screening, over execution delay, maximum condition/calibration processing P95 and serialized model bytes. It does not identify a statistical winner or globally minimal configuration. For X=1 and Y=0:

| Profile | Deadline (s) | Nondominated selected configurations |
|---|---:|---|
| guarded_reference | 3 | DT |
| guarded_reference | 5 | DT |
| guarded_reference | 10 | RULE, DT |
| cpu1_ram512 | 3 | DT, KNN |
| cpu1_ram512 | 5 | DT, KNN |
| cpu1_ram512 | 10 | RULE, DT, KNN |
| cpu05_ram512 | 3 | DT |
| cpu05_ram512 | 5 | DT |
| cpu05_ram512 | 10 | RULE, DT |
| cpu025_ram512 | 3 | DT |
| cpu025_ram512 | 5 | DT |
| cpu025_ram512 | 10 | RULE, DT |

## Reproduce this analysis

```sh
python3 scripts/analyze_docker_pilot.py --run-root /path/to/retained/completed-run --output build/NEW_ANALYSIS
# Add --figures in the pinned scientific environment to regenerate the plots.
```

The retained run bundle, trusted sibling input manifest/workspace and original trace files are required. Compact shipped summaries are not substitutes for those inputs. Analysis refuses to overwrite an output, verifies frozen input hashes, checks actual clock/cgroup limits, and reconstructs queue behavior. provenance.json records source hashes and frozen image identities.

## Limitations for the manuscript

One jamming episode/session, one spoofing session and one supplementary benign development recording. Future-informed ML fits and a development-selected rule threshold. One technical attempt per configuration/profile/session in this repeat; the earlier pilot is technical replication, not new independent data. Annotated onset is not physical jammer-on. No verified attack-end/recovery ground truth. A desktop Linux ARM64 VM is not a calibrated UAV processor. No validated external results or inferential 95% guarantees.
