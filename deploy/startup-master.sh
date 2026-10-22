#!/bin/bash
# Startup-скрипт для ВМ-майстра (образ Container-Optimized OS, Docker уже встановлено).
# Запускає контейнер PARCS-Python у режимі master. Виконується при кожному завантаженні ВМ.
# Власний фаєрвол Container-Optimized OS блокує вхідні з'єднання (крім SSH), а контейнер
# працює в мережі хоста. Дозволяємо вхідні: фільтрацію вже виконує брандмауер VPC.
iptables -w -I INPUT -j ACCEPT
docker rm -f parcs >/dev/null 2>&1 || true
docker run -d --name parcs --restart unless-stopped --network host \
  -e PARCS_ARGS="master" \
  hummer12007/parcs-node
