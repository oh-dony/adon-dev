#!/bin/bash
# Instala receitas de verdade num Ubuntu limpo (Docker), como usuário comum com sudo sem senha.
# Uso: tests/docker/rodar.sh <imagem, ex. ubuntu:24.04> <ids, ex. git,node>
set -e
IMG=$1 IDS=$2
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
docker run --rm -v "$ROOT:/app:ro" "$IMG" bash -c "
  set -e
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq >/dev/null && apt-get install -y -qq python3 sudo >/dev/null
  useradd -m -s /bin/bash dev
  echo 'dev ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/dev
  su - dev -c 'ADON_DEV_ROOT_CMD=\"sudo -n bash\" python3 /app/tests/docker/instalar.py /app $IDS'
"
