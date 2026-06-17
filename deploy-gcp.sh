#!/bin/bash
# Script de deployment para Google Cloud Platform
# Asegúrate de tener instalado gcloud CLI: https://cloud.google.com/sdk/docs/install

set -e  # Salir si hay algún error

# ========== CONFIGURACIÓN ==========
# Modifica estos valores según tu proyecto
PROJECT_ID="tu-proyecto-gcp"
REGION="us-central1"  # o la región que prefieras
SERVICE_NAME="iluma-orders-api"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "🚀 Iniciando deployment a Google Cloud Run"
echo "============================================"
echo "Proyecto: ${PROJECT_ID}"
echo "Región: ${REGION}"
echo "Servicio: ${SERVICE_NAME}"
echo "============================================"

# ========== PASO 1: Verificar autenticación ==========
echo ""
echo "📋 Paso 1/5: Verificando autenticación con GCP..."
if ! gcloud auth print-access-token &> /dev/null; then
    echo "❌ No estás autenticado. Ejecuta: gcloud auth login"
    exit 1
fi
echo "✅ Autenticado correctamente"

# ========== PASO 2: Configurar proyecto ==========
echo ""
echo "📋 Paso 2/5: Configurando proyecto..."
gcloud config set project ${PROJECT_ID}
echo "✅ Proyecto configurado: ${PROJECT_ID}"

# ========== PASO 3: Build de la imagen Docker ==========
echo ""
echo "📋 Paso 3/5: Construyendo imagen Docker..."
echo "Usando: Dockerfile.prod"

# Opción A: Build local y push a GCR
docker build -f Dockerfile.prod -t ${IMAGE_NAME}:latest .
docker push ${IMAGE_NAME}:latest

# Opción B (alternativa): Cloud Build (descomenta si prefieres esta opción)
# gcloud builds submit --tag ${IMAGE_NAME}:latest -f Dockerfile.prod

echo "✅ Imagen construida y subida: ${IMAGE_NAME}:latest"

# ========== PASO 4: Deploy a Cloud Run ==========
echo ""
echo "📋 Paso 4/5: Desplegando a Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE_NAME}:latest \
  --platform managed \
  --region ${REGION} \
  --allow-unauthenticated \
  --port 8000 \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 10 \
  --set-env-vars PYTHONUNBUFFERED=1 \
  --timeout 300

# IMPORTANTE: Las variables de entorno sensibles se deben configurar manualmente
# Usa Secret Manager para credenciales:
# gcloud run services update ${SERVICE_NAME} \
#   --update-secrets=DB_PASSWORD=db-password:latest \
#   --update-secrets=AUTH0_CLIENT_SECRET=auth0-secret:latest

echo "✅ Servicio desplegado en Cloud Run"

# ========== PASO 5: Obtener URL del servicio ==========
echo ""
echo "📋 Paso 5/5: Obteniendo URL del servicio..."
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
  --region ${REGION} \
  --format 'value(status.url)')

echo ""
echo "============================================"
echo "✅ ¡Deployment completado exitosamente!"
echo "============================================"
echo "🌐 URL del servicio: ${SERVICE_URL}"
echo ""
echo "📝 Próximos pasos:"
echo "1. Configurar las variables de entorno en Cloud Run Console"
echo "2. Configurar Cloud SQL para Oracle (si usas Cloud SQL)"
echo "3. Configurar Secret Manager para credenciales sensibles"
echo "4. Actualizar CORS allowed_origin con la URL del frontend"
echo ""
echo "Para ver logs en tiempo real:"
echo "gcloud run services logs tail ${SERVICE_NAME} --region ${REGION}"
echo ""
