#!/usr/bin/env bash
# =============================================================================
# upload_tokens.sh
# Carga los tokens W3C DTCG de Alexandria Magazine a Zeroheight via API.
#
# PREREQUISITOS:
#   1. Obtén tu API key en: https://zeroheight.com/settings/api
#      (Zeroheight Settings → API → Create new token)
#   2. Necesitas tener `curl` y `jq` instalados
#
# USO:
#   export ZH_API_KEY="zh_your_api_key_here"
#   bash upload_tokens.sh
#
#   O directamente:
#   ZH_API_KEY="zh_your_api_key_here" bash upload_tokens.sh
# =============================================================================

set -euo pipefail

# ── Configuración ─────────────────────────────────────────────────────────────

# Tu API key de Zeroheight
ZH_API_KEY="${ZH_API_KEY:-}"

# ID del styleguide de Alexandria Magazine en Zeroheight
# Encontrarlo en: URL del styleguide → zeroheight.com/styleguide/s/XXXXXX
ZH_STYLEGUIDE_ID="${ZH_STYLEGUIDE_ID:-143429}"

# Archivo de tokens DTCG
TOKENS_FILE="$(dirname "$0")/tokens.dtcg.json"

# Base URL de la API de Zeroheight
ZH_API_BASE="https://zeroheight.com/api/v3"

# ── Validaciones ──────────────────────────────────────────────────────────────

if [[ -z "$ZH_API_KEY" ]]; then
  echo "❌ Error: ZH_API_KEY no está configurada."
  echo ""
  echo "   Obtén tu API key en: https://zeroheight.com/settings/api"
  echo "   Luego ejecuta:"
  echo "   ZH_API_KEY=\"tu_api_key_aquí\" bash upload_tokens.sh"
  exit 1
fi

if [[ ! -f "$TOKENS_FILE" ]]; then
  echo "❌ Error: No se encontró el archivo de tokens en: $TOKENS_FILE"
  exit 1
fi

if ! command -v curl &> /dev/null; then
  echo "❌ Error: curl no está instalado."
  exit 1
fi

if ! command -v jq &> /dev/null; then
  echo "⚠️  jq no está instalado — la respuesta JSON no se formateará."
fi

# ── Verificar conexión con la API ─────────────────────────────────────────────

echo "🔍 Verificando conexión con la API de Zeroheight..."

AUTH_CHECK=$(curl --silent --fail \
  --header "Authorization: Bearer $ZH_API_KEY" \
  --header "Accept: application/json" \
  "$ZH_API_BASE/styleguides/$ZH_STYLEGUIDE_ID" \
  2>&1 || true)

if echo "$AUTH_CHECK" | grep -q '"error"'; then
  echo "❌ Error de autenticación. Verifica que tu API key sea válida."
  if command -v jq &> /dev/null; then
    echo "$AUTH_CHECK" | jq '.error // .message // .'
  else
    echo "$AUTH_CHECK"
  fi
  exit 1
fi

echo "✅ Conexión verificada con el styleguide $ZH_STYLEGUIDE_ID"

# ── Cargar tokens ─────────────────────────────────────────────────────────────

echo ""
echo "📤 Cargando tokens de Alexandria Magazine..."
echo "   Archivo: $TOKENS_FILE"
echo "   Tamaño: $(wc -c < "$TOKENS_FILE") bytes"
echo ""

RESPONSE=$(curl --silent --fail \
  --request POST \
  --header "Authorization: Bearer $ZH_API_KEY" \
  --header "Accept: application/json" \
  --header "Content-Type: application/json" \
  --data-binary "@$TOKENS_FILE" \
  "$ZH_API_BASE/styleguides/$ZH_STYLEGUIDE_ID/design_tokens" \
  2>&1 || true)

# ── Resultado ─────────────────────────────────────────────────────────────────

if echo "$RESPONSE" | grep -q '"error"'; then
  echo "❌ Error al cargar los tokens:"
  if command -v jq &> /dev/null; then
    echo "$RESPONSE" | jq '.error // .message // .'
  else
    echo "$RESPONSE"
  fi
  exit 1
fi

echo "✅ Tokens cargados correctamente en Zeroheight."
echo ""

if command -v jq &> /dev/null; then
  echo "📊 Respuesta:"
  echo "$RESPONSE" | jq '.'
else
  echo "📊 Respuesta raw:"
  echo "$RESPONSE"
fi

echo ""
echo "🔗 Ver tokens en:"
echo "   https://zeroheight.com/styleguide/s/$ZH_STYLEGUIDE_ID"
echo ""
echo "ℹ️  Los tokens pueden tardar unos segundos en aparecer en el editor."

# =============================================================================
# NOTA: Si la API de Zeroheight usa un endpoint diferente para tokens,
# ajustar la URL arriba. La API de Zeroheight puede variar según el plan.
# Documentación: https://zeroheight.com/help/article/zeroheight-api/
# =============================================================================
