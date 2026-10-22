#!/usr/bin/env bash
# Видаляє всі ВМ і правила брандмауера кластера PARCS (щоб не витрачати кредити).
set -uo pipefail
ZONE="${ZONE:-europe-central2-a}"

VMS=$(gcloud compute instances list --filter="name~^parcs-" --format="value(name)")
if [ -n "$VMS" ]; then
  gcloud compute instances delete $VMS --zone="$ZONE" --quiet
fi
gcloud compute firewall-rules delete parcs-web parcs-internal --quiet
echo "Кластер видалено."
