# The host controller verifies the immutable parent ID before building and freezes
# both parent and final image IDs. This reuses the already verified pinned deps.
FROM nulp-gnss:limits-v1
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    PYTHONPATH=/opt/research/src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 BLIS_NUM_THREADS=1
COPY src/ /opt/research/src/
ENTRYPOINT ["python", "-m", "gnss_jamming.pilot_runtime"]
