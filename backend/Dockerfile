# Use Ubuntu 20.04 base which is officially supported by Playwright
FROM ubuntu:20.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install Python 3.11 and system dependencies
RUN apt-get update && apt-get install -y \
    software-properties-common \
    curl \
    wget \
    gnupg \
    ca-certificates \
    procps \
    xvfb \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install -y \
    python3.11 \
    python3.11-dev \
    python3.11-distutils \
    python3-pip \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1 \
    && rm -rf /var/lib/apt/lists/*

# Install pip for Python 3.11
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11

WORKDIR /app

# Copy and install Python requirements
COPY requirements.txt .
RUN python3.11 -m pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (this should work better on Ubuntu 20.04)
RUN python3.11 -m playwright install --with-deps chromium
# Verify installation
RUN ls -la /root/.cache/ms-playwright/ || echo "Playwright cache not found"

# Copy application code
COPY . .
