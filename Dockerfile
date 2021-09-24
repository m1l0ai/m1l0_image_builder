# Dockerfile for image builder service
ARG PYTHON=python3
ARG PIP=pip
ARG PYTHON_VERSION=3.6.14

FROM python:${PYTHON_VERSION} AS builder
ARG PYTHON
ARG PIP
ARG PYTHON_VERSION

SHELL ["/bin/bash", "-c"]

COPY requirements.txt .

RUN ${PYTHON} -m venv /myvenv && \
    source /myvenv/bin/activate && \
    ${PYTHON} -m ${PIP} install --upgrade pip setuptools && \
    ${PYTHON} -m ${PIP} install --no-cache-dir -r requirements.txt

RUN apt-get update && apt-get install -y --no-install-recommends -y \
    wget && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install GRPC HEALTH PROBE
RUN GRPC_HEALTH_PROBE_VERSION=v0.4.4 && \
    wget -qO/bin/grpc_health_probe https://github.com/grpc-ecosystem/grpc-health-probe/releases/download/${GRPC_HEALTH_PROBE_VERSION}/grpc_health_probe-linux-amd64 


# Second stage of multistage build
FROM python:${PYTHON_VERSION}-slim
ARG PYTHON
ARG PIP

LABEL maintainer="M1L0 ckyeo.1@gmail.com"
LABEL m1l0.component="builder"
LABEL m1l0.version="1"
LABEL m1l0.python="${PYTHON_VERSION}"

SHELL ["/bin/bash", "-c"]

ENV DEBIAN_FRONTEND=noninteractive \
		TZ=Europe/Moscow \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=UTF-8 \ 
    PATH=/myvenv/bin:$PATH

RUN apt-get update && apt-get install -y --no-install-recommends -y \
    curl \
    vim \
    git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /myvenv /myvenv

COPY ./builder /builder
COPY ./main.py /main.py

# Copy healthprobe
COPY --from=builder /bin/grpc_health_probe /bin/grpc_health_probe

RUN chmod +x /bin/grpc_health_probe

HEALTHCHECK --interval=10s --retries=3 CMD /bin/grpc_health_probe -addr=localhost:50051 -tls -tls-ca-cert=${M1L0_BUILDER_CA_PATH}

ENTRYPOINT ["python", "main.py"]