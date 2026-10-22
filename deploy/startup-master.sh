#!/bin/bash
# Startup-скрипт для ВМ-майстра (образ Container-Optimized OS, Docker уже встановлено).
# Запускає контейнер PARCS-Python у режимі master. Виконується при кожному завантаженні ВМ.
docker rm -f parcs >/dev/null 2>&1 || true
docker run -d --name parcs --restart unless-stopped --network host \
  -e PARCS_ARGS="master" \
  hummer12007/parcs-node
