FROM python:3.12-slim

# Install system packages
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /src

# Copy dependency files first
COPY pyproject.toml uv.lock ./

# INSTALL ONLY the 'run' group
# This ignores [dependencies] and only installs [dependency-groups.run]
RUN uv sync --frozen --only-group run

# Copy project files
COPY /.streamlit /src/.streamlit
COPY /app /src/app
COPY /data/model /src/data/model
COPY /data/processed /src/data/processed

# Expose Streamlit port
EXPOSE 8501

# Healthcheck
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Run Streamlit through uv
CMD ["uv", "run", "streamlit", "run", "app/streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
