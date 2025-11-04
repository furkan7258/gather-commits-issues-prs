# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    NON_INTERACTIVE=1

WORKDIR /app

# Install system deps (if any needed later)
RUN apt-get update -y && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies and install
COPY requirements.txt ./
RUN pip install -r requirements.txt

# Copy source
COPY gather.py ./
COPY csv_to_usernames_json.py ./

# Default output dir inside container
ENV OUTPUT_DIR=/data/output \
    REPOS_FILE=/data/repos.json \
    DATES_FILE=/data/dates.json \
    USERNAMES_FILE=/data/github-usernames.json

# Create mount point
VOLUME ["/data"]

# Command: bake default data paths into ENTRYPOINT so extra flags append
ENTRYPOINT ["python","gather.py","-r","/data/repos.json","-d","/data/dates.json","-o","/data/commits-issues-prs","-u","/data/github-usernames.json"]
# Extra flags provided at docker run will be appended to ENTRYPOINT
CMD []
