# 📁 Docker Publish - Estructura del Proyecto

Esta carpeta contiene **todo lo necesario** para publicar la imagen de Sonarr Size Analyzer en Docker Hub con builds automáticos desde GitHub.

---

## 📦 Archivos Incluidos

### 🐳 Docker Configuration

| Archivo | Tamaño | Propósito |
|---------|--------|-----------|
| **`Dockerfile`** | 2.1 KB | Imagen multi-stage optimizada |
| **`.dockerignore`** | 745 B | Exclusiones para build |
| **`docker-compose.yml`** | 2.1 KB | Ejemplo de composición |

### 🐍 Python Application

| Archivo | Tamaño | Propósito |
|---------|--------|-----------|
| **`app.py`** | 36 KB | Aplicación Streamlit principal |
| **`security.py`** | 7.2 KB | Gestión de credenciales cifradas |
| **`storage.py`** | 18 KB | Base de datos histórica SQLite |
| **`requirements.txt`** | 301 B | Dependencias Python |

### 📚 Documentation

| Archivo | Tamaño | Propósito |
|---------|--------|-----------|
| **`README.md`** | 12.4 KB | **Documentación principal** para Docker Hub |
| **`PUBLISH_GUIDE.md`** | 8.9 KB | **Guía paso a paso** de publicación |
| **`INDEX.md`** | Este archivo | Índice de contenidos |

### ⚙️ Configuration

| Archivo | Propósito |
|---------|-----------|
| **`.gitignore`** | Exclusiones para Git (no commitar datos sensibles) |

---

## 🎯 Propósito de Cada Archivo

### `Dockerfile`
Imagen Docker multi-stage que:
- ✅ Construye con Python 3.11-slim
- ✅ Usuario no-root (UID 1000)
- ✅ Volumen persistente `/app/data`
- ✅ Health check integrado
- ✅ Optimizado para tamaño (~250 MB)

### `.dockerignore`
Excluye del build de Docker:
- Archivos de desarrollo (venv, __pycache__)
- Documentación (.md, .ipynb)
- Datos sensibles (*.db, *.enc, *.csv)
- Archivos de respaldo

### `docker-compose.yml`
Ejemplo de uso con:
- Imagen: `martitoci/sonarr-analyzer:latest`
- Puerto: 8501
- Volumen persistente
- Health checks
- Resource limits
- Security hardening

### `app.py`
Aplicación Streamlit extendida con:
- 📊 Análisis actual de Sonarr
- 📈 Tracking histórico en SQLite
- 🔒 Credenciales cifradas AES-256
- 🔄 Comparación temporal
- 📉 Visualizaciones avanzadas

### `security.py`
Módulo de seguridad:
- Clase `CredentialManager`
- Cifrado AES-256 con Fernet
- Derivación PBKDF2 (100K iteraciones)
- Save/Load/Delete credenciales

### `storage.py`
Módulo de almacenamiento:
- Clase `HistoryDatabase`
- SQLite con 2 tablas
- Save/Load/Compare análisis
- Time-series queries
- Data management (cleanup, export)

### `requirements.txt`
Dependencias necesarias:
```
streamlit==1.29.0
requests==2.31.0
pandas==2.1.4
numpy==1.26.2
plotly==5.18.0
matplotlib==3.8.2
seaborn==0.13.0
cryptography==41.0.7
```

### `README.md`
**Documentación principal** que aparecerá en Docker Hub:
- Quick start con Docker
- Guía de uso completa
- Características destacadas
- Seguridad y encriptación
- Troubleshooting
- Comandos de referencia

### `PUBLISH_GUIDE.md`
**Guía paso a paso** para publicar:
1. Crear repositorio en GitHub
2. Configurar Docker Hub
3. Conectar GitHub ↔ Docker Hub
4. Configurar builds automáticos
5. Trigger y verificar builds
6. Workflow de actualización

### `.gitignore`
Protege contra commits accidentales de:
- Datos sensibles (*.db, *.enc)
- Archivos de desarrollo (venv, __pycache__)
- Credenciales (.env)
- Archivos temporales

---

## 🚀 Uso Rápido

### Para Publicar en Docker Hub

```bash
# 1. Ir a la carpeta
cd docker_publish

# 2. Inicializar git
git init

# 3. Agregar archivos
git add .

# 4. Commit
git commit -m "Initial commit - Sonarr Size Analyzer"

# 5. Conectar con GitHub
git remote add origin https://github.com/martitoci/sonarr-analyzer.git

# 6. Push
git push -u origin main
```

Luego sigue la **PUBLISH_GUIDE.md** para configurar Docker Hub.

### Para Probar Localmente

```bash
# Build local
docker build -t sonarr-analyzer:test .

# Run local
docker run -d \
  --name sonarr-test \
  -p 8501:8501 \
  -v sonarr-data:/app/data \
  sonarr-analyzer:test

# Test
curl http://localhost:8501
```

---

## 📊 Estructura Visual

```
docker_publish/
│
├── 🐳 Docker Files
│   ├── Dockerfile              # Imagen principal
│   ├── .dockerignore          # Exclusiones build
│   └── docker-compose.yml     # Ejemplo uso
│
├── 🐍 Application
│   ├── app.py                 # Aplicación Streamlit
│   ├── security.py            # Módulo cifrado
│   ├── storage.py             # Módulo BD
│   └── requirements.txt       # Dependencias
│
├── 📚 Documentation
│   ├── README.md              # Docs Docker Hub
│   ├── PUBLISH_GUIDE.md       # Guía publicación
│   └── INDEX.md               # Este archivo
│
└── ⚙️ Configuration
    └── .gitignore             # Exclusiones Git
```

---

## ✅ Checklist Pre-Publicación

Antes de subir a GitHub, verifica:

- [x] ✅ `Dockerfile` presente y correcto
- [x] ✅ `.dockerignore` con exclusiones apropiadas
- [x] ✅ `docker-compose.yml` funcionando
- [x] ✅ `app.py`, `security.py`, `storage.py` presentes
- [x] ✅ `requirements.txt` completo
- [x] ✅ `README.md` documentado para Docker Hub
- [x] ✅ `PUBLISH_GUIDE.md` con instrucciones
- [x] ✅ `.gitignore` protegiendo archivos sensibles
- [x] ✅ Build local exitoso
- [x] ✅ Aplicación funciona en contenedor

---

## 🎓 Guías de Lectura

### Para Usuarios Finales
1. **README.md** - Cómo usar la imagen desde Docker Hub

### Para Mantenedores
1. **PUBLISH_GUIDE.md** - Cómo publicar y actualizar
2. **INDEX.md** (este archivo) - Estructura y propósito

### Para Desarrolladores
1. Código fuente: `app.py`, `security.py`, `storage.py`
2. Dockerfile - Proceso de build
3. `.dockerignore` - Qué se excluye

---

## 🔗 Links Importantes

- **Docker Hub:** https://hub.docker.com/r/martitoci/sonarr-analyzer
- **GitHub:** https://github.com/martitoci/sonarr-analyzer
- **Imagen:** `martitoci/sonarr-analyzer:latest`

---

## 📝 Notas Importantes

### ⚠️ No Incluir en Git

**NUNCA** commitear:
- ❌ Archivos de datos (*.db, *.csv)
- ❌ Credenciales cifradas (*.enc, *_salt)
- ❌ Variables de entorno con secrets (.env)
- ❌ Archivos de respaldo (*_backup.py)

### ✅ Sí Incluir

**SÍ** commitear:
- ✅ Código fuente (*.py)
- ✅ Dockerfile y docker-compose.yml
- ✅ Documentación (*.md)
- ✅ requirements.txt
- ✅ .gitignore y .dockerignore

---

## 🎯 Objetivo Final

Al subir esta carpeta a GitHub y conectar con Docker Hub:

1. ✅ **Push a GitHub** → Build automático en Docker Hub
2. ✅ **Imagen disponible** → `martitoci/sonarr-analyzer`
3. ✅ **Usuarios pueden usar** → `docker pull martitoci/sonarr-analyzer`
4. ✅ **Actualizaciones automáticas** → Nuevo push = nueva build

---

## 📞 Soporte

- 📖 **Documentación:** Ver README.md
- 🚀 **Publicación:** Ver PUBLISH_GUIDE.md
- 📁 **Estructura:** Este archivo (INDEX.md)
- 🐛 **Problemas:** GitHub Issues

---

**Todo listo para publicar en Docker Hub!** 🚀🐳

*Sigue la PUBLISH_GUIDE.md para comenzar.*

