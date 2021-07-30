# Dockerfile for image builder service
ARG PYTHON=python3
ARG PIP=pip
ARG PYTHON_VERSION=3.6.14

FROM python:${PYTHON_VERSION} AS builder
ARG PYTHON
ARG PIP
ARG PYTHON_VERSION

COPY requirements.txt .

RUN ${PYTHON} -m ${PIP} install --upgrade pip setuptools && \
    ${PYTHON} -m ${PIP} install --no-cache-dir --user -r requirements.txt


# Second stage of multistage build
FROM python:${PYTHON_VERSION}-slim

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
    PATH=/root/.local:/root/.local/bin:$PATH \
    PYTHONPATH=/gprotobufs

RUN apt-get update && apt-get install -y --no-install-recommends -y \
    curl \
    vim \
    git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*


COPY --from=builder /root/.local /root/.local

COPY ./gprotobufs /gprotobufs

COPY ./builder /builder

ENTRYPOINT ["python", "builder/service.py"]
