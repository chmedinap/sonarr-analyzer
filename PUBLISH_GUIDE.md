# 🚀 Guía de Publicación en Docker Hub

Esta guía te ayudará a publicar la imagen de Sonarr Size Analyzer en Docker Hub con builds automáticos desde GitHub.

---

## 📋 Requisitos Previos

1. ✅ Cuenta en [GitHub](https://github.com)
2. ✅ Cuenta en [Docker Hub](https://hub.docker.com)
3. ✅ Usuario de Docker Hub: `martitoci`

---

## 🔗 Paso 1: Preparar el Repositorio en GitHub

### 1.1 Crear Repositorio en GitHub

1. Ve a https://github.com/new
2. **Repository name:** `sonarr-analyzer` (o el nombre que prefieras)
3. **Description:** "Sonarr Series Size Analyzer - Extended Edition with Historical Tracking"
4. **Visibility:** Public (necesario para builds automáticos gratis)
5. **NO** inicializar con README (ya lo tenemos)
6. Click **"Create repository"**

### 1.2 Preparar los Archivos Localmente

```bash
# Ir a la carpeta docker_publish
cd /Users/cmedinaposso/Downloads/test/docker_publish

# Inicializar git (si no está inicializado)
git init

# Agregar todos los archivos
git add .

# Primer commit
git commit -m "Initial commit - Sonarr Size Analyzer Extended Edition"

# Conectar con GitHub (reemplaza con tu URL)
git remote add origin https://github.com/martitoci/sonarr-analyzer.git

# O si ya existe el remoto:
git remote set-url origin https://github.com/martitoci/sonarr-analyzer.git

# Push a GitHub
git branch -M main
git push -u origin main
```

### 1.3 Verificar en GitHub

- Ve a tu repositorio en GitHub
- Deberías ver todos los archivos:
  - ✅ Dockerfile
  - ✅ app.py
  - ✅ security.py
  - ✅ storage.py
  - ✅ requirements.txt
  - ✅ docker-compose.yml
  - ✅ README.md
  - ✅ .dockerignore
  - ✅ .gitignore

---

## 🐳 Paso 2: Configurar Docker Hub

### 2.1 Crear Repositorio en Docker Hub

1. Inicia sesión en https://hub.docker.com
2. Click en **"Create Repository"**
3. **Name:** `sonarr-analyzer`
4. **Visibility:** Public
5. **Description:** "Sonarr Series Size Analyzer - Historical tracking & encrypted credentials"
6. Click **"Create"**

**Tu imagen será:** `martitoci/sonarr-analyzer`

### 2.2 Conectar Docker Hub con GitHub

1. En Docker Hub, ve a tu repositorio: `martitoci/sonarr-analyzer`
2. Ve a la pestaña **"Builds"**
3. Click **"Configure Automated Builds"**
4. Click **"Connect to GitHub"**
5. Autoriza Docker Hub a acceder a tu GitHub
6. Selecciona tu repositorio: `martitoci/sonarr-analyzer`

### 2.3 Configurar Build Rules

En la sección **"Build Rules"**, configura:

| Source Type | Source | Docker Tag | Dockerfile Location | Build Context |
|-------------|--------|------------|---------------------|---------------|
| Branch | main | latest | Dockerfile | / |
| Tag | `/^v([0-9.]+)$/` | {\1} | Dockerfile | / |

**Explicación:**
- **Branch main → latest:** Cada push a main construye la etiqueta `latest`
- **Tag v* → version:** Un tag `v2.0.0` construye `2.0.0`

### 2.4 Habilitar Autobuild

1. ✅ Activa **"Autobuild"**
2. ✅ (Opcional) Activa **"Build Caching"** para builds más rápidos
3. Click **"Save and Build"**

---

## 🎯 Paso 3: Trigger del Primer Build

### Opción A: Push a main (automático)

Cualquier push a la rama `main` dispara un build:

```bash
# Hacer un cambio (por ejemplo, actualizar README)
echo "# Updated" >> README.md

# Commit y push
git add .
git commit -m "Update README"
git push origin main
```

### Opción B: Crear un Tag (versión)

Para crear una versión específica:

```bash
# Crear tag
git tag -a v2.0.0 -m "Release version 2.0.0 - Extended Edition"

# Push el tag
git push origin v2.0.0
```

Esto creará dos imágenes:
- `martitoci/sonarr-analyzer:latest`
- `martitoci/sonarr-analyzer:2.0.0`

### Opción C: Trigger Manual

1. Ve a Docker Hub → tu repositorio → Builds
2. Click **"Trigger"** junto a la regla de build
3. Espera el build (5-10 minutos)

---

## 📊 Paso 4: Verificar el Build

### 4.1 Monitor en Docker Hub

1. Ve a https://hub.docker.com/r/martitoci/sonarr-analyzer/builds
2. Verás el estado del build:
   - 🔵 **Pending:** En cola
   - 🟡 **Building:** Construyendo
   - 🟢 **Success:** Completado
   - 🔴 **Error:** Falló

### 4.2 Ver Logs

Si el build falla:
1. Click en el build fallido
2. Lee los logs para identificar el error
3. Corrige el problema
4. Push nuevamente

### 4.3 Tiempo Estimado

- **Primer build:** 8-12 minutos
- **Builds subsecuentes:** 5-8 minutos (con cache)

---

## ✅ Paso 5: Probar la Imagen

Una vez que el build sea exitoso:

```bash
# Pull la imagen
docker pull martitoci/sonarr-analyzer:latest

# Ejecutar
docker run -d \
  --name sonarr-analyzer-test \
  -p 8501:8501 \
  -v sonarr-data:/app/data \
  martitoci/sonarr-analyzer:latest

# Verificar logs
docker logs -f sonarr-analyzer-test

# Abrir en navegador
# http://localhost:8501
```

---

## 🔄 Paso 6: Workflow de Actualización

### Para Actualizaciones Regulares

```bash
# 1. Hacer cambios en el código
vim app.py  # o cualquier archivo

# 2. Commit
git add .
git commit -m "Fix: descripción del cambio"

# 3. Push (dispara build automático)
git push origin main

# 4. Esperar build en Docker Hub (~5-10 min)

# 5. Usuarios pueden actualizar con:
docker pull martitoci/sonarr-analyzer:latest
docker stop sonarr-analyzer
docker rm sonarr-analyzer
docker run -d --name sonarr-analyzer -p 8501:8501 -v sonarr-data:/app/data martitoci/sonarr-analyzer:latest
```

### Para Releases con Versión

```bash
# 1. Hacer cambios y test
# ... desarrollo ...

# 2. Commit
git add .
git commit -m "Release v2.1.0: Nueva característica"

# 3. Crear tag
git tag -a v2.1.0 -m "Release 2.1.0"

# 4. Push código y tags
git push origin main
git push origin v2.1.0

# 5. Docker Hub creará:
#    - martitoci/sonarr-analyzer:latest
#    - martitoci/sonarr-analyzer:2.1.0
```

---

## 🛡️ Seguridad y Best Practices

### No Incluir en Git/Docker

❌ **NUNCA** commitar:
- API keys
- Passphrases
- Archivos de datos (`.db`, `.csv`)
- Credenciales cifradas (`.enc`)
- Variables de entorno con secrets

✅ **Sí incluir:**
- Código fuente (`.py`)
- Dockerfile
- requirements.txt
- Documentación (`.md`)
- Archivos de configuración de ejemplo

### Proteger el Repositorio

```bash
# Verificar .gitignore antes de commit
cat .gitignore

# Ver qué se va a commitear
git status

# Si algo sensible aparece, agregarlo a .gitignore:
echo "archivo_sensible.txt" >> .gitignore
git add .gitignore
git commit -m "Update gitignore"
```

---

## 📈 Monitoreo y Mantenimiento

### Ver Estadísticas en Docker Hub

1. Ve a https://hub.docker.com/r/martitoci/sonarr-analyzer
2. Verás:
   - **Pulls:** Número de descargas
   - **Stars:** Popularidad
   - **Last pushed:** Última actualización

### Badges para README

Agregar al README de GitHub:

```markdown
[![Docker Pulls](https://img.shields.io/docker/pulls/martitoci/sonarr-analyzer.svg)](https://hub.docker.com/r/martitoci/sonarr-analyzer)
[![Docker Image Size](https://img.shields.io/docker/image-size/martitoci/sonarr-analyzer/latest)](https://hub.docker.com/r/martitoci/sonarr-analyzer)
```

---

## 🐛 Troubleshooting

### Build Falla con "No such file or directory"

**Problema:** Dockerfile no encuentra `app.py`, `security.py`, etc.

**Solución:**
```bash
# Verificar que los archivos estén en el repo
ls -la
# Deben estar: app.py, security.py, storage.py

# Si faltan, copiarlos
cp ../app.py ../security.py ../storage.py .

# Commit y push
git add .
git commit -m "Add missing Python files"
git push origin main
```

### Build Falla con "pip install error"

**Problema:** Error instalando dependencias

**Solución:**
```bash
# Verificar requirements.txt
cat requirements.txt

# Probar localmente
pip install -r requirements.txt

# Si funciona local, rebuild en Docker Hub
```

### La imagen no se actualiza

**Problema:** Pull muestra versión antigua

**Solución:**
```bash
# Forzar pull sin cache
docker pull --no-cache martitoci/sonarr-analyzer:latest

# O eliminar imagen local primero
docker rmi martitoci/sonarr-analyzer:latest
docker pull martitoci/sonarr-analyzer:latest
```

---

## 📝 Checklist Final

Antes de publicar, verifica:

- [ ] ✅ Repositorio creado en GitHub
- [ ] ✅ Código subido a GitHub
- [ ] ✅ Repositorio creado en Docker Hub
- [ ] ✅ GitHub conectado con Docker Hub
- [ ] ✅ Build rules configuradas
- [ ] ✅ Autobuild habilitado
- [ ] ✅ Primer build exitoso
- [ ] ✅ Imagen pull funciona
- [ ] ✅ Aplicación corre correctamente
- [ ] ✅ README.md documentado
- [ ] ✅ .gitignore configurado
- [ ] ✅ Sin archivos sensibles en repo

---

## 🎉 ¡Listo!

Tu imagen ahora está publicada en Docker Hub y se actualizará automáticamente con cada push a GitHub.

**Tu imagen:** https://hub.docker.com/r/martitoci/sonarr-analyzer

**Usuarios pueden usar:**
```bash
docker pull martitoci/sonarr-analyzer:latest
docker run -d --name sonarr-analyzer -p 8501:8501 -v sonarr-data:/app/data martitoci/sonarr-analyzer:latest
```

---

## 📞 Soporte

- **Docker Hub:** https://hub.docker.com/r/martitoci/sonarr-analyzer
- **GitHub:** https://github.com/martitoci/sonarr-analyzer
- **Issues:** Crear issue en GitHub para problemas

---

**¡Feliz publicación!** 🚀🐳

