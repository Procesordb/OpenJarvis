---
title: Deployment
description: Deploy AGI PROCESOR in production environments
---

# Deployment

AGI PROCESOR supports multiple deployment strategies for different environments
and scales.

## Docker

The recommended way to deploy AGI PROCESOR in production. Multi-stage builds
with CPU and GPU (NVIDIA CUDA, AMD ROCm) variants.

[:octicons-arrow-right-24: Docker deployment](docker.md)

## systemd (Linux)

Run AGI PROCESOR as a managed system service on Linux servers.

[:octicons-arrow-right-24: systemd setup](systemd.md)

## launchd (macOS)

Register AGI PROCESOR as a launch agent on macOS.

[:octicons-arrow-right-24: launchd setup](launchd.md)

## API Server

Run AGI PROCESOR as an OpenAI-compatible HTTP server via `agi serve`.

[:octicons-arrow-right-24: API server guide](api-server.md)
