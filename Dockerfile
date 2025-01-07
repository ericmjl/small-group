FROM ghcr.io/prefix-dev/pixi:latest

COPY pyproject.toml .
COPY pixi.lock .
COPY run.py .
COPY app app
COPY src src
RUN pixi self-update
RUN pixi install

ENV PORT=8147
EXPOSE $PORT
ENTRYPOINT ["pixi", "run", "python", "run.py", "--db-path", "/app/data/prod.db"]
