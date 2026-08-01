FROM python:3.14-slim

ENV PYTHONPATH=/bot \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /bot

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install Python dependencies
COPY pyproject.toml ./
RUN uv sync --no-dev

# Copy application code
COPY files/ ./files/
COPY core/ ./core/
COPY sfa_bot/ ./sfa_bot/
COPY config.toml ./

CMD ["uv", "run", "--no-sync", "python", "sfa_bot"]
