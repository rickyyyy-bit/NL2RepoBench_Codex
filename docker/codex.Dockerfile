FROM node:22-bookworm AS node
FROM python:3.12-bookworm
COPY --from=node /usr/local/ /usr/local/
ARG CODEX_VERSION
RUN test -n "$CODEX_VERSION" && npm install -g "@openai/codex@$CODEX_VERSION" \
    && apt-get update && apt-get install -y --no-install-recommends git ripgrep ca-certificates \
    && rm -rf /var/lib/apt/lists/*
LABEL org.nl2repobench.codex-version=$CODEX_VERSION
ENV HOME=/home/codex CODEX_HOME=/home/codex/.codex PYTHONDONTWRITEBYTECODE=1
WORKDIR /workspace
ENTRYPOINT ["codex"]
