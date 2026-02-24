FROM python:3.14-slim

# The Agent SDK bundles its own CLI but needs Node.js at runtime
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl git ca-certificates gnupg && \
    mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_22.x nodistro main" > /etc/apt/sources.list.d/nodesource.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md ./
COPY caveclaw/ caveclaw/
COPY agents/ agents/

RUN pip install --no-cache-dir .

RUN useradd -m caveclaw
USER caveclaw

ENTRYPOINT ["caveclaw"]
CMD ["agent"]
