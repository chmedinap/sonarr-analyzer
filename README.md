# 📊 Sonarr Series Size Analyzer - Extended Edition

[![Docker Hub](https://img.shields.io/docker/pulls/martitoci/sonarr-analyzer.svg)](https://hub.docker.com/r/martitoci/sonarr-analyzer)
[![Docker Image Size](https://img.shields.io/docker/image-size/martitoci/sonarr-analyzer/latest)](https://hub.docker.com/r/martitoci/sonarr-analyzer)
[![Python Version](https://img.shields.io/badge/python-3.11-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](https://opensource.org/licenses/MIT)

A professional web application built with Streamlit for analyzing average file size per episode across TV series managed by Sonarr. **Now with historical tracking, encrypted credential storage, and temporal comparison!**

---

## 🚀 Quick Start with Docker

### Pull and Run (Recommended)

```bash
# Pull the latest image
docker pull martitoci/sonarr-analyzer:latest

# Run with persistent data
docker run -d \
  --name sonarr-analyzer \
  -p 8501:8501 \
  -v sonarr-data:/app/data \
  --restart unless-stopped \
  martitoci/sonarr-analyzer:latest
```

**Access the application:** http://localhost:8501

### Using Docker Compose

Create a `docker-compose.yml` file:

```yaml
version: '3.8'

services:
  sonarr-analyzer:
    image: martitoci/sonarr-analyzer:latest
    container_name: sonarr-analyzer
    ports:
      - "8501:8501"
    volumes:
      - sonarr-data:/app/data
    restart: unless-stopped

volumes:
  sonarr-data:
```

Then run:

```bash
docker-compose up -d
```

---

## ✨ Features

### 🔒 **Secure Credential Management**
- **AES-256 Encryption** for storing Sonarr credentials
- **Master Passphrase** protection
- No plain-text API keys stored
- Easy credential loading/deletion

### 📈 **Historical Analysis**
- **SQLite Database** for tracking analysis history
- **Unlimited historical records** (with optional cleanup)
- Track changes over time for each series
- Compare any two analysis dates

### 🔄 **Temporal Comparison**
- **Side-by-side comparison** of two dates
- **Detect new/removed series** automatically
- **Storage change tracking** (GB and %)
- **Trend visualization** for individual series

### 📊 **Advanced Visualizations**
- **Storage evolution** over time
- **Average size trends** globally and per-series
- **Episode count tracking**
- **Top changers** between dates

---

## 📖 Usage Guide

### First Time Setup

1. **Start the container** (see Quick Start above)
2. **Open your browser:** http://localhost:8501
3. **Go to ⚙️ Configuration** (sidebar)
4. **Enter your Sonarr credentials:**
   - Sonarr URL (e.g., `http://192.168.1.10:8989`)
   - API Key (from Sonarr → Settings → General → Security)
5. **(Optional) Save credentials encrypted:**
   - Check "I want to save these credentials encrypted"
   - Create a strong passphrase (min 8 characters)
   - Confirm passphrase
   - Click "Save Encrypted Credentials"

### Running Your First Analysis

1. **Go to 🔍 Current Analysis** (sidebar)
2. Configure advanced options if needed:
   - Request timeout
   - Z-Score threshold
   - Absolute threshold
   - ✅ **Enable "Save this analysis to history"**
3. Click **🚀 Run Analysis**
4. Wait for results (progress bar shows status)
5. Explore results in tabs:
   - **📋 Table:** All series with metrics
   - **📊 Charts:** Visual representations
   - **🚨 Outliers:** Problematic series

### Using Historical Data

#### View All Analyses

1. **Go to 📈 Historical Data** (sidebar)
2. **Tab: 📅 All Analyses**
3. See:
   - Table of all past analyses
   - Storage evolution chart
   - Average size trends chart

#### Compare Two Dates

1. **Tab: 🔄 Compare Dates**
2. **Select two dates** to compare
3. Click **🔄 Compare**
4. Review:
   - **Summary metrics:** New/removed series, storage change
   - **Detailed table:** Per-series comparison
   - **Top changers chart:** Biggest changes
5. **Download comparison CSV** for external analysis

---

## 🔐 Security Features

### Credential Encryption

The application uses **Fernet (AES-128)** with **PBKDF2 key derivation**:

- **Salt:** Random 16-byte salt (stored in `.sonarr_salt`)
- **Iterations:** 100,000 PBKDF2 rounds
- **Key derivation:** SHA-256
- **Encryption:** AES-128-CBC via Fernet

**Files created in volume:**
- `data/.sonarr_credentials.enc` (encrypted credentials)
- `data/.sonarr_salt` (salt for key derivation)
- `data/sonarr_history.db` (SQLite database - not encrypted)

**Best practices:**
1. Use a **strong passphrase** (12+ characters, mixed case, numbers, symbols)
2. **Never share** your passphrase
3. Backup your data volume regularly
4. **Passphrase cannot be recovered** if lost

---

## 💾 Data Persistence

### Using Named Volume (Recommended)

```bash
docker run -d \
  --name sonarr-analyzer \
  -p 8501:8501 \
  -v sonarr-data:/app/data \
  martitoci/sonarr-analyzer:latest
```

**Backup volume:**
```bash
docker run --rm \
  -v sonarr-data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/sonarr-data-backup.tar.gz -C /data .
```

**Restore volume:**
```bash
docker run --rm \
  -v sonarr-data:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/sonarr-data-backup.tar.gz -C /data
```

### Using Local Directory

```bash
# Create local directory
mkdir -p ./sonarr-data

# Run with local mount
docker run -d \
  --name sonarr-analyzer \
  -p 8501:8501 \
  -v $(pwd)/sonarr-data:/app/data \
  martitoci/sonarr-analyzer:latest
```

**Files will be in:** `./sonarr-data/`

---

## 📊 Understanding the Results

### Z-Score Explained

The **Z-Score** measures how many standard deviations a value is from the mean:

```
Z-Score = (Value - Mean) / Std Deviation
```

**Interpretation:**

| Z-Score | Meaning | Action |
|---------|---------|--------|
| 0 to 1 | Normal ✅ | No action needed |
| 1 to 2 | Slightly high ⚠️ | Monitor |
| **> 2** | **Outlier 🚨** | **Review and re-encode** |
| > 3 | Extreme 🔥 | **High priority** |

**Real example:**
- Mean: 675 MB per episode
- Std Dev: 567 MB
- Series with 2000 MB: Z-Score = 2.34 → **Outlier!**

This series uses ~3x more space than average.

### Metrics Glossary

- **Episodes:** Number of downloaded episode files
- **Total Size (GB):** Combined size of all episodes
- **Avg Size (MB):** Average file size per episode
- **Z-Score:** Statistical deviation (see above)
- **Outlier:** Yes if Z-Score > threshold (default: 2.0)

---

## 🔧 Configuration

### Environment Variables

You can configure the application using environment variables:

```bash
docker run -d \
  --name sonarr-analyzer \
  -p 8501:8501 \
  -e STREAMLIT_SERVER_PORT=8501 \
  -e STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
  -v sonarr-data:/app/data \
  martitoci/sonarr-analyzer:latest
```

**Available variables:**
- `STREAMLIT_SERVER_PORT` (default: 8501)
- `STREAMLIT_SERVER_ADDRESS` (default: 0.0.0.0)
- `STREAMLIT_SERVER_HEADLESS` (default: true)
- `STREAMLIT_BROWSER_GATHER_USAGE_STATS` (default: false)

### Custom Port

```bash
# Run on port 9000
docker run -d \
  --name sonarr-analyzer \
  -p 9000:8501 \
  -v sonarr-data:/app/data \
  martitoci/sonarr-analyzer:latest
```

Access at: http://localhost:9000

---

## 🐳 Docker Image Details

### Image Information

- **Base Image:** python:3.11-slim
- **Architecture:** linux/amd64, linux/arm64
- **Size:** ~250 MB
- **User:** Non-root (UID 1000)
- **Health Check:** Built-in

### Ports

- **8501:** Streamlit web interface

### Volumes

- **/app/data:** Persistent storage for:
  - Historical analysis database
  - Encrypted credentials (optional)
  - Configuration files

### Tags

- `latest` - Latest stable release
- `v2.0.0` - Specific version
- `v2` - Major version

```bash
# Use specific version
docker pull martitoci/sonarr-analyzer:v2.0.0

# Use latest
docker pull martitoci/sonarr-analyzer:latest
```

---

## 🔍 Troubleshooting

### Cannot connect to Sonarr

**Problem:** App shows "Connection failed"

**Solutions:**
1. **Check Sonarr is running**
2. **Verify URL format:**
   - ✅ Good: `http://192.168.1.10:8989`
   - ❌ Bad: `192.168.1.10:8989` (missing http://)
   - ❌ Bad: `localhost:8989` (from inside container)
3. **Use host IP or container name** if in same network
4. **Check firewall rules**

### Invalid passphrase

**Problem:** Cannot load saved credentials

**Solutions:**
1. **Try passphrase again** (case-sensitive)
2. **Delete and recreate:**
   ```bash
   docker exec sonarr-analyzer rm /app/data/.sonarr_credentials.enc /app/data/.sonarr_salt
   ```
3. **Reconfigure** in ⚙️ Configuration page

### No historical data

**Problem:** Historical Data page is empty

**Solutions:**
1. **Run an analysis first** with "Save to history" enabled
2. **Check database exists:**
   ```bash
   docker exec sonarr-analyzer ls -la /app/data/
   ```
3. **Verify volume is mounted:**
   ```bash
   docker inspect sonarr-analyzer | grep Mounts -A 20
   ```

### High memory usage

**Problem:** Container using too much RAM

**Solutions:**
1. **Set memory limits:**
   ```bash
   docker run -d \
     --name sonarr-analyzer \
     -p 8501:8501 \
     -v sonarr-data:/app/data \
     --memory="1g" \
     --memory-swap="1g" \
     martitoci/sonarr-analyzer:latest
   ```

2. **Cleanup old analyses:**
   - Go to 📈 Historical Data → Manage Data
   - Use "Cleanup old data" feature

---

## 📈 Use Cases

### Monthly Storage Audit

```bash
# Run analysis on 1st of each month
# Compare with previous month
# Identify series consuming most storage
# Decision: Re-encode or delete
```

### Pre/Post Re-encoding Comparison

```bash
# Before re-encoding: Run analysis
# Re-encode series with high Z-scores
# After re-encoding: Run analysis again
# Compare dates to see savings
```

### Library Growth Tracking

```bash
# Weekly/monthly analyses
# Monitor storage evolution chart
# Plan storage upgrades proactively
```

---

## 🛠️ Building from Source

If you want to build the image locally:

```bash
# Clone the repository
git clone https://github.com/yourusername/sonarr-analyzer.git
cd sonarr-analyzer/docker_publish

# Build the image
docker build -t martitoci/sonarr-analyzer:latest .

# Run your build
docker run -d \
  --name sonarr-analyzer \
  -p 8501:8501 \
  -v sonarr-data:/app/data \
  martitoci/sonarr-analyzer:latest
```

---

## 🔄 Automated Builds

This repository is connected to Docker Hub for **automated builds**:

- ✅ **Push to GitHub** → Automatic build on Docker Hub
- ✅ **Multi-architecture** support (amd64, arm64)
- ✅ **Automated testing** before deployment
- ✅ **Tagged releases** for version control

**Docker Hub:** https://hub.docker.com/r/martitoci/sonarr-analyzer

---

## 📝 Version History

### v2.0.0 - Extended Edition (Latest)
- ➕ Added credential encryption (AES-256)
- ➕ Added SQLite historical database
- ➕ Added date comparison feature
- ➕ Added trend visualizations
- ➕ Added per-series tracking
- ➕ Added configuration page
- ➕ Added historical data page
- 🔧 Improved UI navigation
- 🐳 Enhanced Docker support

### v1.0.0 - Standard Edition
- Initial release
- Current analysis
- Z-score detection
- Outlier identification
- Interactive visualizations
- CSV export

---

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create feature branch
3. Test thoroughly
4. Submit pull request

---

## 📄 License

MIT License - See LICENSE file for details

---

## 🙏 Acknowledgments

- **Streamlit** - Web framework
- **Plotly** - Interactive charts
- **Cryptography** - Secure encryption
- **Pandas** - Data analysis
- **Sonarr Team** - Amazing media management

---

## 📞 Support

- 🐳 **Docker Hub:** https://hub.docker.com/r/martitoci/sonarr-analyzer
- 📧 **Issues:** GitHub Issues
- 💬 **Discussions:** GitHub Discussions
- 📖 **Documentation:** Full docs in repository

---

## ⚡ Quick Commands Reference

```bash
# Pull latest image
docker pull martitoci/sonarr-analyzer:latest

# Run with persistent data
docker run -d --name sonarr-analyzer -p 8501:8501 -v sonarr-data:/app/data martitoci/sonarr-analyzer:latest

# View logs
docker logs -f sonarr-analyzer

# Stop container
docker stop sonarr-analyzer

# Remove container
docker rm sonarr-analyzer

# Backup data
docker run --rm -v sonarr-data:/data -v $(pwd):/backup alpine tar czf /backup/backup.tar.gz -C /data .

# Update to latest
docker pull martitoci/sonarr-analyzer:latest
docker stop sonarr-analyzer
docker rm sonarr-analyzer
docker run -d --name sonarr-analyzer -p 8501:8501 -v sonarr-data:/app/data martitoci/sonarr-analyzer:latest
```

---

**Made with ❤️ for the Sonarr community**

*Track, compare, and optimize your Sonarr library!* 📊✨

**Docker Hub:** https://hub.docker.com/r/martitoci/sonarr-analyzer

