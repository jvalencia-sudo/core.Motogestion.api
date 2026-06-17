# 🔄 Guía para Actualizar el Backend en Google Cloud

## 📋 Información del Deployment Actual

- **Proyecto GCP:** oracle-462001
- **Servicio Cloud Run:** iluma-orders-api
- **Región:** us-central1
- **URL Actual:** https://iluma-orders-api-839613239565.us-central1.run.app
- **Imagen Docker:** gcr.io/oracle-462001/iluma-orders-api:v2

## 🚀 Prompt para Actualizar el Backend

Copia y pega este prompt en Claude Code cuando necesites subir cambios:

---

```
Necesito actualizar el backend desplegado en Google Cloud Run con mis últimos cambios.

INFORMACIÓN DEL DEPLOYMENT:
- Proyecto GCP: oracle-462001
- Servicio: iluma-orders-api
- Región: us-central1
- Dockerfile: Dockerfile.prod
- Imagen base: gcr.io/oracle-462001/iluma-orders-api

TAREAS:

1. Verifica que todos mis cambios estén guardados (usa git status si es necesario)

2. Construye la nueva imagen Docker usando Dockerfile.prod:
   - Usa un nuevo tag con la fecha/versión (ejemplo: v3, v2024-11-28, etc.)
   - El comando debe ser: docker build -f Dockerfile.prod -t gcr.io/oracle-462001/iluma-orders-api:TAG .

3. Sube la imagen a Google Container Registry:
   - docker push gcr.io/oracle-462001/iluma-orders-api:TAG

4. Actualiza el servicio en Cloud Run:
   - Usa: gcloud run services update iluma-orders-api --image gcr.io/oracle-462001/iluma-orders-api:TAG --region us-central1
   - O si prefieres hacer un deploy completo con todas las configuraciones

5. Verifica que el deployment fue exitoso:
   - Revisa los logs: gcloud run services logs read iluma-orders-api --region us-central1 --limit 50
   - Prueba el health check: curl https://iluma-orders-api-839613239565.us-central1.run.app/

6. Si hay errores, muéstrame los logs y ayúdame a solucionarlos

IMPORTANTE:
- NO cambies las variables de entorno a menos que te lo indique específicamente
- La base de datos Oracle está en la IP privada: 10.128.0.5
- El servicio debe usar el VPC connector: cloud-run-connector
```

---

## ⚡ Comando Rápido (Si solo quieres actualizar el código)

Si prefieres hacerlo manualmente de forma rápida:

```bash
# 1. Build y push en un solo paso
docker build -f Dockerfile.prod -t gcr.io/oracle-462001/iluma-orders-api:latest . && \
docker push gcr.io/oracle-462001/iluma-orders-api:latest

# 2. Actualizar Cloud Run
gcloud run services update iluma-orders-api \
  --image gcr.io/oracle-462001/iluma-orders-api:latest \
  --region us-central1

# 3. Verificar
curl https://iluma-orders-api-839613239565.us-central1.run.app/
```

## 🔧 Si Necesitas Actualizar Variables de Entorno

```bash
gcloud run services update iluma-orders-api \
  --region us-central1 \
  --update-env-vars NOMBRE_VARIABLE=nuevo_valor
```

## 📊 Comandos Útiles

### Ver logs en tiempo real:
```bash
gcloud run services logs tail iluma-orders-api --region us-central1
```

### Ver todas las revisiones del servicio:
```bash
gcloud run revisions list --service iluma-orders-api --region us-central1
```

### Rollback a una revisión anterior:
```bash
gcloud run services update-traffic iluma-orders-api \
  --region us-central1 \
  --to-revisions NOMBRE_REVISION=100
```

### Ver detalles del servicio:
```bash
gcloud run services describe iluma-orders-api --region us-central1
```

## ⚠️ Troubleshooting

Si el deployment falla:

1. **Verifica que la imagen se construyó correctamente:**
   ```bash
   docker images | grep iluma-orders-api
   ```

2. **Prueba la imagen localmente primero:**
   ```bash
   docker run -p 8000:8000 --env-file .env gcr.io/oracle-462001/iluma-orders-api:latest
   ```

3. **Revisa los logs del deployment:**
   ```bash
   gcloud run services logs read iluma-orders-api --region us-central1 --limit 100
   ```

4. **Verifica que Oracle esté corriendo:**
   ```bash
   gcloud compute ssh oracle-db --zone us-central1-a --command "docker ps"
   ```

## 📝 Notas Importantes

- **Siempre haz backup** de tu código antes de desplegar (commit en git)
- **Prueba localmente** antes de desplegar a producción
- **Usa tags versionados** en lugar de `:latest` para producción
- **El deployment toma 2-3 minutos** en completarse
- **Cloud Run hace rollout gradual** automáticamente
