FROM ghcr.io/prefix-dev/pixi:latest

WORKDIR /app

COPY pyproject.toml .
COPY pixi.lock .
COPY run.py .
COPY app app
COPY src src
RUN pixi self-update
RUN pixi install

EXPOSE 8164
ENTRYPOINT ["pixi", "run", "python", "run.py", "--db-path", "/app/data/prod.db"]
