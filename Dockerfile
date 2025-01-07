FROM ghcr.io/prefix-dev/pixi:latest

COPY pyproject.toml .
COPY pixi.lock .
COPY run.py .
COPY app app
COPY src src
RUN pixi self-update
RUN pixi install

EXPOSE 5000
ENTRYPOINT ["pixi", "run", "python", "run.py", "--db-path", "/app/data/prod.db"]
