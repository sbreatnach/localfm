FROM docker.io/library/python:3.14-slim
COPY --from=docker.io/astral/uv:0.9.26 /uv /uvx /bin/
RUN apt update && apt install -y libpq5 --no-install-recommends

# Disable development dependencies
ENV UV_NO_DEV=1
# setup environment for running project
RUN mkdir -p /app && chown www-data:www-data /app
WORKDIR /app
USER www-data

# install dependencies
COPY --chown=www-data:www-data uv.lock pyproject.toml ./
RUN uv sync --no-cache --locked

# copy project files
COPY --chown=www-data:www-data manage.py localfm/ ./
COPY --chown=www-data:www-data localfm/ ./localfm/
COPY --chown=www-data:www-data deployment/scripts/ ./deployment/scripts/

CMD ["uv", "run", "--no-cache", "python", "-m", "localfm.main"]
