FROM ghcr.io/guiltjay/crawl4ai:latest
WORKDIR /app

# Keep dependency installation cacheable while application code changes.
COPY requirements.txt ./
RUN python3 -m pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x run_pipeline.sh missav_pipeline.sh onejav_pipeline.sh javct_pipeline.sh aggregator_pipeline.sh scripts/*.sh scripts/*.py || true
CMD ["bash", "./run_pipeline.sh"]
