FROM python:3.12-slim

# Install system packages
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files first
COPY pyproject.toml uv.lock ./

# INSTALL ONLY the 'run' group
# This ignores [dependencies] and only installs [dependency-groups.run]
RUN uv sync --frozen --only-group run

# Copy project files
COPY /.streamlit /app/
COPY /app /app/
COPY /data/model /app/
COPY /data/processed /app/

# Expose Streamlit port
EXPOSE 8501

# Healthcheck
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Run Streamlit through uv
CMD ["uv", "run", "streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
