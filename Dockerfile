# The explorer app (default) and the command line, in one image.
#
#   docker build -t steel-ontology .
#   docker run --rm -p 8501:8501 steel-ontology                  # app on http://localhost:8501
#   docker run --rm steel-ontology steel-ontology validate examples/kestrel-platform/gold.json
#
# Model providers read their key from the environment, e.g. --env-file .env (see .env.example).
# HermiT needs Java and is not installed here; the pure-Python OWL RL reasoner is.

FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.13 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies first, so a source change does not reinstall them.
COPY pyproject.toml uv.lock README.md LICENSE ./
RUN uv sync --frozen --no-dev --no-install-project \
        --extra app --extra anthropic --extra openai --extra gemini

COPY ontology ./ontology
COPY src ./src
COPY app ./app
COPY examples ./examples
RUN uv sync --frozen --no-dev \
        --extra app --extra anthropic --extra openai --extra gemini

RUN useradd --create-home --uid 1000 steel && chown -R steel /app
USER steel

EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health')"

CMD ["streamlit", "run", "app/explorer.py", \
     "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true", \
     "--browser.gatherUsageStats=false"]
