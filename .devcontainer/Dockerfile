# funding-rate-alert 开发容器(Telegram 通知 + 币安 API)
FROM python:3.9-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
        git curl ca-certificates iptables ipset dnsutils sudo \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/* \
    && npm install -g @anthropic-ai/claude-code

ARG USERNAME=dev
RUN useradd -m -s /bin/bash $USERNAME \
    && echo "$USERNAME ALL=(root) NOPASSWD: /usr/local/bin/init-firewall.sh" > /etc/sudoers.d/firewall \
    && chmod 0440 /etc/sudoers.d/firewall

COPY init-firewall.sh /usr/local/bin/init-firewall.sh
RUN chmod 0755 /usr/local/bin/init-firewall.sh && chown root:root /usr/local/bin/init-firewall.sh

USER $USERNAME
WORKDIR /workspace
ENV PATH="/home/dev/.local/bin:${PATH}"
