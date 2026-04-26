FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

WORKDIR /app

COPY pyproject.toml .
RUN uv sync

COPY src/ src/

EXPOSE 8080

CMD ["uv", "run", "python", "src/wp-mcp/server.py"]
