FROM python:3.14-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install Python dependencies
COPY pyproject.toml ./
RUN uv sync --no-dev

# Copy application code
COPY core/ ./core/
COPY sfa_bot/ ./sfa_bot/
COPY config.toml ./

CMD ["uv", "run", "python", "-m", "sfa_bot"]
