#!/bin/bash
# Startup-скрипт для ВМ-воркера (образ Container-Optimized OS).
# Внутрішню IP-адресу майстра беремо з метаданих ВМ (ключ parcs-master-ip),
# які задає create_cluster.sh, і запускаємо контейнер PARCS-Python у режимі worker.
MASTER_IP=$(curl -s -H "Metadata-Flavor: Google" \
  "http://metadata.google.internal/computeMetadata/v1/instance/attributes/parcs-master-ip")
docker rm -f parcs >/dev/null 2>&1 || true
docker run -d --name parcs --restart unless-stopped --network host \
  -e PARCS_ARGS="worker ${MASTER_IP}" \
  hummer12007/parcs-node
