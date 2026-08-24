FROM jupyter/pyspark-notebook:latest

USER root

# =========================
# 1. Chromium correcto en Ubuntu 22.04 (NO "chromium")
# =========================
RUN apt-get update && apt-get install -y \
    ca-certificates \
    openssl \
    curl \
    supervisor \
    wget \
    chromium-browser \
    chromium-chromedriver \
    fonts-liberation \
    libnss3 \
    libxss1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libx11-xcb1 \
    libdrm2 \
    libgbm1 \
    xdg-utils \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# =========================
# 2. Python libs
# =========================
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    selenium pandas pymongo dnspython certifi beautifulsoup4 requests

# =========================
# 3. Spark Mongo connector
# =========================
# We rely on Spark package loading at runtime (PYSPARK_SUBMIT_ARGS or spark.jars.packages)
# instead of manually downloading connector jars that can create version conflicts.

# =========================
# 4. Supervisor
# =========================
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
