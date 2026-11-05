# GNSS-jamming detector configuration selection

Terminology for evaluating timely detection, false alarms and resource feasibility within a finite detector library.

## Language

**Detector configuration**:
A complete candidate: features, processing, algorithm and parameters, decision threshold, confirmation, recovery and execution platform.
_Avoid_: Using “model” to refer to the entire detector

**Resource profile**:
Declared limits on available computing resources in a specific evaluation environment. A profile is not equivalent to another physical device.
_Avoid_: Emulating an SBC through a CPU fraction

**Readiness check**:
A check that the environment starts, limits are applied and selected models can produce a trial decision. It does not establish timely detection or resource consumption under the full workload.
_Avoid_: A completed resource experiment

**Message processing time**:
The execution interval for processing one message within the declared software boundary. Queue waiting time is accounted for separately.
_Avoid_: Attack detection delay

**Confirmed alarm delay**:
The interval from the declared episode onset to the actual readiness of a new confirmed alarm. It includes waiting for available observations, queueing and detector execution.
_Avoid_: Model prediction time or the triggering sample timestamp

**Resource feasibility**:
A configuration's satisfaction of declared resource requirements in the tested environment. This alone does not establish functional feasibility.
_Avoid_: Overall PASS based on a single speed metric

**Feasible configuration**:
A configuration satisfying all applicable functional requirements and resource constraints for a scenario. An unmeasured mandatory requirement leaves feasibility undetermined.
_Avoid_: The accuracy winner

**Smallest tested profile**:
The smallest feasible profile among the studied candidates under the declared ordering of resource limits. Incomparable profiles may yield multiple alternatives; global minimality is not established.
_Avoid_: Universally minimal resources

**Technical repetition**:
Repeated execution on the same data to describe measurement variability. It does not create a new independent session or attack episode.
_Avoid_: Independent confirmation through the number of passes

**Literature precedent**:
A verified account of a specific technique in prior work, with explicit limits on relevance. It supports the choice of technique but does not confirm our detector's results or equivalence to other hardware.
_Avoid_: A paper as proof of our hardware equivalence

**Local prototype check**:
An executed check of an implemented component or pipeline against specified inputs and criteria. It is distinct from verification of scientific sources.
_Avoid_: Calling a discovered reference an executed prototype

**Attack episode**:
A declared interval of interference with a defined onset and evaluation applicability conditions. Multiple episodes may belong to one recording and remain dependent.
_Avoid_: Using independent session as a synonym for episode
