#!/usr/bin/env bash
# Створює кластер PARCS-Python у Google Cloud: 1 майстер + $WORKERS воркерів.
#
#   MY_IP=<ваша_публічна_IP> ./deploy/create_cluster.sh
#
# Змінні середовища (необов'язкові):
#   ZONE     - зона (за замовчуванням europe-central2-a, Варшава)
#   MACHINE  - тип ВМ (за замовчуванням n1-standard-1: 1 vCPU)
#   WORKERS  - кількість воркерів (за замовчуванням 6; разом з майстром 7 vCPU,
#              free trial дозволяє не більше 8 vCPU одночасно)
#   MY_IP    - публічна IP вашого комп'ютера, з якого відкриватимете веб-інтерфейс
set -euo pipefail

ZONE="${ZONE:-europe-central2-a}"
MACHINE="${MACHINE:-n1-standard-1}"
WORKERS="${WORKERS:-6}"
DIR="$(cd "$(dirname "$0")" && pwd)"

if [ -z "${MY_IP:-}" ]; then
  echo "Задайте MY_IP - публічну IP вашого комп'ютера (дізнатися: https://api.ipify.org у браузері)."
  echo "Приклад: MY_IP=93.170.12.34 ./deploy/create_cluster.sh"
  exit 1
fi
# IP середовища, де запущено скрипт (Cloud Shell / ваш ПК) - для bench.py
SHELL_IP="$(curl -s https://api.ipify.org)"

gcloud config set compute/zone "$ZONE" >/dev/null
echo ">> Вмикаю Compute Engine API (може зайняти хвилину)..."
gcloud services enable compute.googleapis.com

echo ">> Правила брандмауера"
if ! gcloud compute firewall-rules describe parcs-internal >/dev/null 2>&1; then
  # вузли PARCS спілкуються між собою (HTTP 8080 + випадкові порти Pyro4)
  gcloud compute firewall-rules create parcs-internal --network=default \
    --direction=INGRESS --action=ALLOW --rules=tcp,udp,icmp \
    --source-tags=parcs --target-tags=parcs
fi
gcloud compute firewall-rules delete parcs-web --quiet >/dev/null 2>&1 || true
# веб-інтерфейс майстра відкритий тільки для вашої IP і для IP цього shell
gcloud compute firewall-rules create parcs-web --network=default \
  --direction=INGRESS --action=ALLOW --rules=tcp:8080 \
  --source-ranges="${MY_IP}/32,${SHELL_IP}/32" --target-tags=parcs-master

COMMON=(--zone="$ZONE" --machine-type="$MACHINE"
        --image-family=cos-stable --image-project=cos-cloud
        --boot-disk-size=10GB)

echo ">> Створюю майстра"
gcloud compute instances create parcs-master "${COMMON[@]}" \
  --tags=parcs,parcs-master \
  --metadata-from-file=startup-script="$DIR/startup-master.sh"

MASTER_INTERNAL=$(gcloud compute instances describe parcs-master --zone="$ZONE" \
  --format='get(networkInterfaces[0].networkIP)')
MASTER_EXTERNAL=$(gcloud compute instances describe parcs-master --zone="$ZONE" \
  --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

echo ">> Створюю $WORKERS воркер(ів), майстер: $MASTER_INTERNAL"
NAMES=()
for i in $(seq 1 "$WORKERS"); do NAMES+=("parcs-worker-$i"); done
gcloud compute instances create "${NAMES[@]}" "${COMMON[@]}" \
  --tags=parcs \
  --metadata=parcs-master-ip="$MASTER_INTERNAL" \
  --metadata-from-file=startup-script="$DIR/startup-worker.sh"

cat <<EOF

Готово. Через 1-3 хвилини (поки завантажиться Docker-образ) відкрийте:
    http://${MASTER_EXTERNAL}:8080
На вкладці Workers мають з'явитися ${WORKERS} воркер(ів).
Для bench.py:  export MASTER=http://${MASTER_EXTERNAL}:8080
EOF
