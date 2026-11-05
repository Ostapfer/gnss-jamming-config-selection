# IGASPIN conditional ordinal adapter

adapter.py is the measured study's byte-identical offline decoder/association implementation. replay.py preserves the offline diagnostic replay function, extracted from its machine-specific historical launcher. Neither fits models. Model loading is intentionally not an automatic command: only locally trusted, separately generated or retained artifacts may be supplied to replay().

## Obtain and check inputs

Acquire the two records separately from IGASPIN. data_manifest.json identifies exact filenames and SHA256 values; it contains no receiver observations. Provider metadata and permission binding remain distinct from the hashes.

```sh
python3 scripts/prepare_igaspin_inputs.py --raw-root /path/to/separately-obtained-records --output build/igaspin-inputs-NEW
```

This standard-library command checks both raw hashes and NAV counts and prepares four ordinal streams under ignored build/. It refuses an existing destination and never loads a model. The projected data stay private. Preparation alone is not a diagnostic experiment or a resource benchmark. The source-time gate, calibration, model provenance and new-run acceptance remain required.

## Adapter contract

Validate all UBX/NMEA checksums and frame continuity. Accept NAV-PVT length 92 with validDate/validTime, calendar UTC plus signed nano, strictly increasing integer UTC. For each NAV after the first require exactly one complete MON-RF between previous NAV end and current NAV start. First NAV remains unavailable; never substitute a future RF message. Keep both RF positions as ordinal 0/1, including duplicate literal blockId0; their physical band/epoch identity is unverified. Convert hAcc/vAcc millimetres to eph/epv metres. They are receiver accuracy estimates, not ground-truth coordinate errors or DOP.

The joint RF/NAV availability check applies even to eph-only models. tAcc=0xffffffff exclusion is inherited study policy, not an asserted documented protocol sentinel. Calibration starts from the first NAV, including its unavailable observation. Missing data do not mean interference and do not close an active event. Provider-reference timing is conditional; no physical-onset or FAR claim is inferred.

## Resource use

See docker/igaspin for the measured runtime bridge, fixed scope and portable Compose mount substitution. The bridge excludes UBX decoding from timed work. The historical 80-trial orchestration and retained trained bundle are not a turnkey public replay package; no untested relocated controller is presented as verified. New model fitting or a new hardware run creates a new experiment identity.
