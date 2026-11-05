# Results draft: Docker resource-sensitivity experiment

## Experimental scope

Five previously selected detector configurations were evaluated using original-rate replay of three development recordings: one jamming session, one spoofing session and one supplementary benign session. The four supervised configurations used noise and horizontal-accuracy features; the rule configuration used noise alone. The supervised models had been fitted using the same development episodes, including attack observations. Their detection results are therefore development diagnostics rather than independent evidence of generalization. The rule used online clean calibration, but its threshold had been selected after development exploration.

The detector ran in an isolated Linux ARM64 container on the declared Mac Docker Desktop VM. Three controlled profiles allocated 1, 0.5 or 0.25 CPU with a 512 MiB memory limit. A guarded reference had no CPU quota and a 1536 MiB limit. The CPU period was 100 ms, swap was disabled, and numerical-library thread limits were one. The independent replay source and collector occupied a separate container with its own 512 MiB limit and unrestricted CPU. Consequently, detector memory limits do not represent the total allocation of the two-container pipeline. The fixed-512-MiB contrasts are more directly interpretable than comparisons with the reference, which also changes the memory ceiling.

The completed repeat comprised 60 sequential configuration/profile/recording attempts. All attempts exited normally, with complete input/result sequences, valid source scheduling, no dropped messages and no forced cleanup intervention. The earlier pilot and its five abnormal or cleanup-affected exits were preserved separately; technical repetitions did not add independent recording sessions.

## Event behavior and detection delay

Across the four resource profiles, raw decision scores, detector states, confirmation counts and event sample boundaries were identical for every configuration/recording pair. Confirmed execution delays from the annotated development onset ranged from 1.9874 to 1.9940 s for Decision Tree, 2.0012 to 2.0803 s for Random Forest, 2.9844 to 2.9922 s for KNN, 2.9833 to 2.9868 s for SVM, and 7.9863 to 7.9959 s for the noise threshold rule. These values refer to the same single attack episode. KNN and SVM observations lay close to the experimental 3 s deadline. The annotated onset was not independently verified as physical jammer activation.

For each configuration/profile, the recordings supplied 445.046782 s of benign exposure and 18.983952 s of spoofing exposure after calibration. No benign false events were observed. SVM generated one false jamming event during the spoofing interval, with 14.993830 s of observed false-active time, approximately 78.98% of that interval. The event was right-censored at the recording end. Its full duration is unknown. The other selected configurations produced no observed spoofing false events. These short exposures do not establish low operational false-alarm rates; exposure must not be multiplied by the number of profiles or repeated replays.

## Resource sensitivity

Random Forest exhibited the clearest processing-tail sensitivity. Its recording-level processing P95 ranged from 96.04 to 101.58 ms at 0.25 CPU, compared with 32.45 to 34.31 ms at 1 CPU under the same 512 MiB ceiling. Post-calibration throttling counters support interpreting this as quota-associated tail growth. Low average CPU consumption at a roughly 1 Hz input rate does not preclude throttling of individual processing bursts within the 100 ms quota period. The other algorithms did not exhibit a uniform monotonic P95 ordering. A single attempt per pair and uncontrolled host/VM activity do not support statistical speed rankings or an isolated causal effect estimate.

Startup also changed with quota. Median marker-bounded startup times for the supervised configurations were approximately 13–15 s at 0.25 CPU and approximately 1 s at 1 CPU. These intervals run from the first pre-import marker to model readiness and exclude earlier interpreter/container work. Replay begins after model readiness, so startup is reported separately from attack-onset detection delay.

Sampled detector cgroup maxima ranged from approximately 46 to 108 MiB. The separate source/collector contributed approximately 15–17 MiB of sampled charge. Sampling occurred every 100 ms; kernel peak-memory counters were unavailable. These values do not establish intrinsic model memory or a minimum deployable memory budget. No profile below 512 MiB was tested.

An event sweep over accepted-ingress and processing-start timestamps showed a maximum of one waiting message in every trial, with no accumulation to two or more waiting messages. This corrects the interpretation of the original zero-valued summary field, which sampled immediately after processing began. Queue occupancy integrated over time matched the sum of individual waiting times. The original trace and summary artifacts were not modified.

## Finite-library screening and limitations

The existing sensitivity grid was applied separately within each enforced resource profile. SVM violated the tested spoofing false-event requirements. The rule did not meet the 3 or 5 s detection deadlines in this episode. Descriptive Pareto sets over confirmed delay, maximum condition/calibration processing P95 and serialized model size retained tradeoffs rather than imposing one universal winner. Front membership can depend on noisy single-run latency summaries; it is not an inferential ranking.

The experiment demonstrates the proposed measurement and screening procedure on a small, development-informed subset. It does not establish target-UAV processor equivalence, global resource minimality, generalizable ML detection performance, recovery from a physically documented jammer-off transition, or operational false-alarm reliability. All statistical evidence remains INSUFFICIENT EVIDENCE. Independent compatible recordings with documented interference timing are required for the next validation stage.
