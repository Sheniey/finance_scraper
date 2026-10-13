
# ================================================== #
# ARGUMENTS                                          #
# ================================================== #

ARG PYTHON_VERSION=3.14



# ================================================== #
# BUILD STAGE                                        #
# ================================================== #

FROM python:${PYTHON_VERSION}-slim AS builder

ARG PYTHON_VERSION

COPY --from=rust:1.88-slim /usr/local/cargo /usr/local/cargo
COPY --from=rust:1.88-slim /usr/local/rustup /usr/local/rustup
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

ENV CARGO_HOME=/usr/local/cargo
ENV RUSTUP_HOME=/usr/local/rustup
ENV PATH="/usr/local/cargo/bin:$PATH"
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    build-essential
RUN rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./
COPY src/ ./src/

RUN uv sync --frozen


# ================================================== #
# RUNTIME STAGE                                      #
# ================================================== #

FROM python:${PYTHON_VERSION}-slim AS runtime

ARG PYTHON_VERSION

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PATH="/app/.venv/bin:$PATH"

COPY --from=builder /app/.venv /app/.venv

COPY src ./src
COPY api ./api
COPY stubs ./stubs
COPY scripts ./scripts
COPY finance-cli.py .
COPY finance-dev.py .
COPY pyproject.toml .

CMD ["python", "-m", "finance-cli"]
