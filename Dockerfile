FROM ghcr.io/guiltjay/crawl4ai:latest

WORKDIR /app


COPY scripts/ ./scripts/
COPY run_pipeline.sh .
RUN chmod +x scripts/* || true
RUN chmod +x run_pipeline.sh || true

CMD ["./run_pipeline.sh"]
