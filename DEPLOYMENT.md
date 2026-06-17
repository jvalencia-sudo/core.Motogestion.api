# 🚀 Guía de Deployment en Google Cloud Platform

Esta guía te ayudará a desplegar la API en Google Cloud Run.

## 📋 Pre-requisitos

1. **Cuenta de Google Cloud Platform** con facturación habilitada
2. **gcloud CLI instalado**: https://cloud.google.com/sdk/docs/install
3. **Docker instalado** en tu máquina local
4. **Base de datos Oracle** accesible desde GCP (Cloud SQL, Oracle Cloud, o auto-hospedada)

## 🔧 Configuración Inicial

### 1. Instalar y configurar gcloud CLI

```bash
# Instalar gcloud CLI (si no lo tienes)
# Ver: https://cloud.google.com/sdk/docs/install

# Autenticarte
gcloud auth login

# Configurar tu proyecto
gcloud config set project TU-PROJECT-ID

# Habilitar APIs necesarias
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable secretmanager.googleapis.com
```

### 2. Configurar Docker para GCR (Google Container Registry)

```bash
gcloud auth configure-docker
```

## 🏗️ Opciones de Deployment

### Opción A: Cloud Run (Recomendado - Más Simple)

Cloud Run es serverless, escala automáticamente y solo pagas por lo que usas.

#### Paso 1: Editar script de deployment

Abre `deploy-gcp.sh` y modifica estas variables:

```bash
PROJECT_ID="tu-proyecto-gcp"      # Tu Project ID de GCP
REGION="us-central1"               # Región donde desplegar
SERVICE_NAME="iluma-orders-api"    # Nombre del servicio
```

#### Paso 2: Dar permisos de ejecución al script

```bash
chmod +x deploy-gcp.sh
```

#### Paso 3: Ejecutar deployment

```bash
./deploy-gcp.sh
```

#### Paso 4: Configurar variables de entorno

Después del deployment, configura las variables de entorno en Cloud Run Console o por CLI:

```bash
# Configurar variables de entorno públicas
gcloud run services update iluma-orders-api \
  --region us-central1 \
  --update-env-vars \
    DB_HOST=tu-oracle-host,\
    DB_PORT=1521,\
    DB_USER=tu-usuario,\
    DB_SERVICE_NAME=XE,\
    environment=production,\
    project_name="Iluma Orders API",\
    allowed_origin=https://tu-frontend.com,\
    frontend_url=https://tu-frontend.com,\
    AUTH0_DOMAIN=tu-tenant.auth0.com,\
    AUTH0_API_AUDIENCE=https://tu-api-audience,\
    AUTH0_ALGORITHMS=RS256

# Configurar secrets (credenciales sensibles) usando Secret Manager
gcloud secrets create db-password --data-file=- <<< "tu-password-de-db"
gcloud secrets create auth0-client-secret --data-file=- <<< "tu-auth0-secret"

# Dar acceso al servicio a los secrets
gcloud run services update iluma-orders-api \
  --region us-central1 \
  --update-secrets \
    DB_PASSWORD=db-password:latest,\
    AUTH0_MANAGEMENT_CLIENT_SECRET=auth0-client-secret:latest
```

### Opción B: Deployment Manual

Si prefieres hacerlo paso por paso:

```bash
# 1. Build de la imagen
docker build -f Dockerfile.prod -t gcr.io/TU-PROJECT-ID/iluma-orders-api:latest .

# 2. Push a Google Container Registry
docker push gcr.io/TU-PROJECT-ID/iluma-orders-api:latest

# 3. Deploy a Cloud Run
gcloud run deploy iluma-orders-api \
  --image gcr.io/TU-PROJECT-ID/iluma-orders-api:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8000 \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 10
```

## 🗄️ Configuración de Base de Datos Oracle

### Opción 1: Oracle en Cloud SQL
Si usas Cloud SQL para Oracle, obtén la IP privada y úsala como `DB_HOST`.

### Opción 2: Oracle Cloud Database
Usa la IP pública o privada (si usas VPC Peering) de tu base de datos Oracle Cloud.

### Opción 3: Oracle Auto-hospedado
Asegúrate que:
- La instancia Oracle tenga una IP pública o esté en la misma VPC
- El firewall permita conexiones desde Cloud Run
- Usa Cloud SQL Proxy si es necesario

## 🔒 Seguridad

### Variables de entorno sensibles

**NUNCA** pongas credenciales directamente en el código o Dockerfile. Usa Secret Manager:

```bash
# Crear un secret
gcloud secrets create mi-secreto --data-file=/path/to/secret

# Dar acceso al servicio de Cloud Run
gcloud secrets add-iam-policy-binding mi-secreto \
  --member=serviceAccount:TU-SERVICE-ACCOUNT@TU-PROJECT.iam.gserviceaccount.com \
  --role=roles/secretmanager.secretAccessor

# Usar el secret en Cloud Run
gcloud run services update iluma-orders-api \
  --update-secrets=MI_VARIABLE=mi-secreto:latest
```

## 📊 Monitoreo y Logs

### Ver logs en tiempo real

```bash
gcloud run services logs tail iluma-orders-api --region us-central1
```

### Ver métricas en Cloud Console

1. Ve a Cloud Run en GCP Console
2. Selecciona tu servicio
3. Ve a la pestaña "Metrics" o "Logs"

## 🔄 Actualizar la aplicación

Cada vez que hagas cambios:

```bash
# Opción 1: Usar el script
./deploy-gcp.sh

# Opción 2: Manual
docker build -f Dockerfile.prod -t gcr.io/TU-PROJECT-ID/iluma-orders-api:latest .
docker push gcr.io/TU-PROJECT-ID/iluma-orders-api:latest
gcloud run deploy iluma-orders-api \
  --image gcr.io/TU-PROJECT-ID/iluma-orders-api:latest \
  --region us-central1
```

## 🌐 Configurar Dominio Personalizado

1. Ve a Cloud Run Console
2. Selecciona tu servicio
3. Click en "Manage Custom Domains"
4. Sigue las instrucciones para mapear tu dominio

## 💰 Costos Estimados

Cloud Run cobra por:
- **Tiempo de CPU**: ~$0.00002400 por vCPU-segundo
- **Memoria**: ~$0.00000250 por GiB-segundo
- **Requests**: Primeros 2 millones gratis, luego $0.40 por millón

Con tráfico bajo-medio, espera ~$5-20/mes.

## 🆘 Troubleshooting

### Error: "Container failed to start"
- Revisa los logs: `gcloud run services logs read iluma-orders-api`
- Verifica que el puerto 8000 esté expuesto
- Verifica variables de entorno

### Error de conexión a Oracle
- Verifica que `DB_HOST` sea accesible desde Cloud Run
- Verifica firewall de Oracle
- Verifica credenciales

### Timeout errors
- Aumenta el timeout: `--timeout 300`
- Aumenta memoria/CPU si es necesario

## 📚 Recursos Adicionales

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Secret Manager](https://cloud.google.com/secret-manager/docs)
- [Cloud SQL for Oracle](https://cloud.google.com/sql/docs/oracle)
