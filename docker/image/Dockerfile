FROM python:3.12.12-slim-bookworm@sha256:593bd06efe90efa80dc4eee3948be7c0fde4134606dd40d8dd8dbcade98e669c
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    PYTHONPATH=/opt/research/src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 MPLCONFIGDIR=/tmp/matplotlib
WORKDIR /opt/research
COPY requirements-lock.txt ./requirements-lock.txt
RUN pip install --no-cache-dir --only-binary=:all: -r requirements-lock.txt
COPY src/ ./src/
COPY probe.py ./probe.py
ENTRYPOINT ["python", "/opt/research/probe.py"]
