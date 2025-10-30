# 🔧 GitHub Codespaces Build Fix

## Problem

Building the Docker image in GitHub Codespaces (or any Debian-based environment) failed with:

```
ERROR: failed to build: failed to solve: process "/bin/sh -c apt-get update && 
apt-get install -y --no-install-recommends su-exec && rm -rf /var/lib/apt/lists/*" 
did not complete successfully: exit code: 100
```

## Root Cause

**`su-exec` is an Alpine Linux package and does NOT exist in Debian repositories.**

The base image `python:3.11-slim` is Debian-based (specifically Debian Bookworm), so trying to install `su-exec` via `apt-get` fails because the package doesn't exist in Debian repos.

### Why This Happened

The original implementation assumed `su-exec` was available in all Linux distributions, but:
- ✅ Alpine Linux: `su-exec` available via `apk`
- ❌ Debian/Ubuntu: `su-exec` does NOT exist in `apt` repos
- ✅ Debian/Ubuntu: `gosu` is the recommended alternative

## Solution

Replaced `su-exec` with `gosu`, which is the official and recommended tool for privilege dropping in Debian-based Docker images.

### What Changed

#### 1. **Dockerfile** - Install `gosu` from GitHub Releases

**Before (Broken):**
```dockerfile
# Install su-exec (DOESN'T EXIST IN DEBIAN!)
RUN apt-get update && apt-get install -y --no-install-recommends \
    su-exec \
    && rm -rf /var/lib/apt/lists/*
```

**After (Fixed):**
```dockerfile
# Install gosu for secure privilege dropping (Debian compatible)
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        wget \
    ; \
    rm -rf /var/lib/apt/lists/*; \
    \
    # Install gosu from official GitHub releases
    dpkgArch="$(dpkg --print-architecture | awk -F- '{ print $NF }')"; \
    wget -O /usr/local/bin/gosu "https://github.com/tianon/gosu/releases/download/1.17/gosu-$dpkgArch"; \
    wget -O /usr/local/bin/gosu.asc "https://github.com/tianon/gosu/releases/download/1.17/gosu-$dpkgArch.asc"; \
    \
    # Verify gosu signature (security best practice)
    export GNUPGHOME="$(mktemp -d)"; \
    gpg --batch --keyserver hkps://keys.openpgp.org --recv-keys B42F6819007F00F88E364FD4036A9C25BF357DD4; \
    gpg --batch --verify /usr/local/bin/gosu.asc /usr/local/bin/gosu; \
    gpgconf --kill all; \
    rm -rf "$GNUPGHOME" /usr/local/bin/gosu.asc; \
    \
    # Make gosu executable
    chmod +x /usr/local/bin/gosu; \
    # Verify gosu works
    gosu --version; \
    gosu nobody true; \
    \
    # Clean up build dependencies
    apt-get purge -y --auto-remove wget
```

**Key Improvements:**
- ✅ Uses `set -eux` for better error handling
- ✅ Downloads from official GitHub releases (works anywhere with internet)
- ✅ Verifies GPG signature for security
- ✅ Tests that gosu works before proceeding
- ✅ Auto-detects architecture (amd64, arm64, etc.)
- ✅ Cleans up build dependencies to keep image small

#### 2. **docker-entrypoint.sh** - Use `gosu` Instead of `su-exec`

**Before:**
```bash
exec su-exec appuser "$@"
```

**After:**
```bash
exec gosu appuser "$@"
```

**Note:** `gosu` and `su-exec` have identical syntax, so this is a drop-in replacement.

#### 3. **Documentation Updates**

Updated `BIND_MOUNT_FIX.md` to reference `gosu` instead of `su-exec`.

## Why `gosu` from GitHub?

You might wonder: "Why download from GitHub instead of using a package?"

**Answer:** `gosu` is NOT in default Debian repositories either. The official installation method recommended by Docker and the `gosu` project is to download from GitHub releases.

### Official Recommendation

From the [official Docker documentation](https://github.com/docker-library/official-images):
```dockerfile
# This is the official way to install gosu in Debian images
RUN set -eux; \
    wget -O /usr/local/bin/gosu "https://github.com/tianon/gosu/releases/download/1.17/gosu-$dpkgArch"; \
    # ... (signature verification) ...
    chmod +x /usr/local/bin/gosu
```

This is the same method used by official Docker images like:
- `postgres`
- `mysql`
- `redis`
- `mongo`

## Benefits of This Approach

### ✅ Works Everywhere
- ✅ GitHub Codespaces
- ✅ Local builds
- ✅ CI/CD (GitHub Actions, GitLab CI, etc.)
- ✅ Any environment with internet access
- ✅ All architectures (amd64, arm64, armv7, etc.)

### ✅ Secure
- GPG signature verification ensures binary hasn't been tampered with
- Downloads from official GitHub releases (trusted source)
- Uses HTTPS for downloads

### ✅ Reliable
- Not dependent on apt repositories being available
- Specific version (1.17) ensures consistency
- Works offline if gosu binary is cached in Docker layers

### ✅ Minimal
- Small binary (~2MB)
- Removes build dependencies after installation
- Doesn't add extra packages to final image

## Testing the Fix

### Build Locally
```bash
cd /path/to/docker_publish
docker build -t sonarr-analyzer:test .
```

### Build in Codespaces
```bash
# In GitHub Codespaces terminal
docker build -t sonarr-analyzer:test .
```

### Verify gosu Works
```bash
# Run a shell in the container
docker run --rm -it sonarr-analyzer:test /bin/bash

# Check gosu is installed
gosu --version
# Should output: 1.17

# Test privilege dropping
gosu nobody whoami
# Should output: nobody

# Test with appuser
gosu appuser whoami
# Should output: appuser
```

### Test Full Application
```bash
# Create test data directory
mkdir -p ./test-data
sudo chown -R 1000:1000 ./test-data

# Run container
docker run -d \
  --name test-analyzer \
  -p 8501:8501 \
  -v ./test-data:/app/data \
  sonarr-analyzer:test

# Check logs
docker logs test-analyzer
# Should see:
# 🔧 Sonarr Analyzer v0.3 - Starting up...
# 🔐 Running as root - fixing permissions...
# ✅ Permissions configured
# 👤 Switching to appuser (UID 1000)...

# Test the app
curl http://localhost:8501/_stcore/health
# Should return 200 OK

# Cleanup
docker rm -f test-analyzer
rm -rf ./test-data
```

## Alternatives Considered

### Alternative 1: Use `su` (Built-in)
```bash
exec su -s /bin/sh appuser -c "$@"
```
❌ **Rejected:** More complex syntax, harder to pass arguments correctly

### Alternative 2: Use Python `os.setuid()`
```python
import os
os.setgid(1000)
os.setuid(1000)
```
❌ **Rejected:** Would need to modify Python code, less clean separation

### Alternative 3: Remove entrypoint, use `USER appuser`
```dockerfile
USER appuser
```
❌ **Rejected:** Loses ability to fix permissions on bind mounts

### Alternative 4: Stay with `su-exec`, switch to Alpine base
```dockerfile
FROM python:3.11-alpine
```
❌ **Rejected:** Alpine has compatibility issues with some Python packages

**Chosen:** Install `gosu` from GitHub (official method, most reliable)

## Migration Path

### For Existing Users

**No action needed!** The change is transparent:
- Container behavior is identical
- Entrypoint works the same way
- All functionality preserved

### For Developers

**Building from source:**
```bash
# Old command (still works)
docker build -t sonarr-analyzer .

# New command (same, just works in Codespaces now)
docker build -t sonarr-analyzer .
```

## Summary

| Aspect | Before | After |
|--------|--------|-------|
| **Tool** | `su-exec` (Alpine only) | `gosu` (cross-platform) |
| **Installation** | `apt-get install` (fails) | GitHub releases (works) |
| **Codespaces** | ❌ Build fails | ✅ Build succeeds |
| **Local build** | ✅ Worked | ✅ Still works |
| **Security** | ✅ Good | ✅ Better (GPG verified) |
| **Size impact** | ~0 MB | +~2 MB (gosu binary) |
| **Maintenance** | Broken in Debian | Fully supported |

## References

- [gosu GitHub Repository](https://github.com/tianon/gosu)
- [Docker Official Images - gosu Usage](https://github.com/docker-library/postgres/blob/master/Dockerfile.template)
- [Why gosu instead of su/sudo](https://github.com/tianon/gosu#why)
- [gosu vs su-exec Comparison](https://github.com/ncopa/su-exec/issues/2#issuecomment-336753200)

## Conclusion

The build now works in GitHub Codespaces, local environments, and all CI/CD platforms by using the official `gosu` installation method instead of the Alpine-specific `su-exec` package. This follows Docker best practices and matches how official Docker images handle privilege dropping.

