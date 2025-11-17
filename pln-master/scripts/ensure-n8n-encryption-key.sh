#!/usr/bin/env bash
set -euo pipefail

# Garante a existência de ./volumes/n8n/config com um encryptionKey estável.
# Se já existir, mantém. Se não existir, gera uma chave nova e grava.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
N8N_DIR="$ROOT_DIR/volumes/n8n"
CONFIG_FILE="$N8N_DIR/config"

mkdir -p "$N8N_DIR"

if [[ -f "$CONFIG_FILE" ]]; then
  echo "✅ Arquivo de configuração do n8n já existe: $CONFIG_FILE"
  # Valida JSON simples
  if ! jq -e . "$CONFIG_FILE" >/dev/null 2>&1; then
    echo "⚠️ Arquivo config existe mas não é JSON válido. Fazendo backup e recriando..."
    cp "$CONFIG_FILE" "$CONFIG_FILE.bak.$(date +%s)"
  else
    echo "🔐 Mantendo encryptionKey existente."
    exit 0
  fi
fi

# Gerar uma chave randômica base64 de 32 bytes
KEY="$(openssl rand -base64 24)"

cat > "$CONFIG_FILE" <<JSON
{
  "encryptionKey": "$KEY"
}
JSON

chmod 600 "$CONFIG_FILE"
echo "✅ Gerado arquivo $CONFIG_FILE com encryptionKey estável."


