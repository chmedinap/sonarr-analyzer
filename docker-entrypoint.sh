#!/bin/bash
set -e

# Sonarr Analyzer Docker Entrypoint
# Ensures proper permissions for bind mounts before starting the app

echo "🔧 Sonarr Analyzer v0.3 - Starting up..."

# Data directory
DATA_DIR="/app/data"

# Ensure data directory exists
if [ ! -d "$DATA_DIR" ]; then
    echo "📁 Creating data directory: $DATA_DIR"
    mkdir -p "$DATA_DIR"
fi

# Check if we're running as root (UID 0)
if [ "$(id -u)" = "0" ]; then
    echo "🔐 Running as root - fixing permissions for bind mounts..."
    
    # Set proper ownership for data directory
    # This ensures bind mounts work correctly
    chown -R appuser:appuser "$DATA_DIR" 2>/dev/null || {
        echo "⚠️  Warning: Could not change ownership of $DATA_DIR"
        echo "    This is normal for some bind mount configurations."
        echo "    If you encounter permission errors, please run on host:"
        echo "    sudo chown -R 1000:1000 /path/to/data"
    }
    
    # Set proper permissions (755 for directory, 644 for files)
    chmod -R u+rwX,go+rX,go-w "$DATA_DIR" 2>/dev/null || {
        echo "⚠️  Warning: Could not set permissions on $DATA_DIR"
    }
    
    echo "✅ Permissions configured"
    echo "👤 Switching to appuser (UID 1000)..."
    
    # Drop privileges and run as appuser
    exec su-exec appuser "$@"
else
    echo "👤 Running as appuser (UID $(id -u))"
    
    # Check if data directory is writable
    if [ ! -w "$DATA_DIR" ]; then
        echo "❌ ERROR: Data directory is not writable!"
        echo ""
        echo "   The container user (UID $(id -u)) cannot write to: $DATA_DIR"
        echo ""
        echo "   For bind mounts, please run on your host machine:"
        echo "   sudo chown -R $(id -u):$(id -g) /path/to/your/data/directory"
        echo ""
        echo "   Or use a named volume instead:"
        echo "   docker run -v sonarr-data:/app/data ..."
        echo ""
        exit 1
    fi
    
    echo "✅ Data directory is writable"
    
    # Execute the main command
    exec "$@"
fi

