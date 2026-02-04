FROM ghcr.io/guiltjay/crawl4ai:latest
WORKDIR /app
COPY . .
RUN chmod +x run_pipeline.sh scripts/*.sh || true
CMD ["bash", "./run_pipeline.sh"]
