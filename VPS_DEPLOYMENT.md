# 🚀 VPS Deployment Guide

## Overview
This guide covers deploying the LLM-TradeBot to a remote VPS for 24/7 automated trading.

---

## 🎯 Deployment Options

### Option 1: Docker (Recommended - Easiest)
- Pre-configured environment
- Isolated from VPS system
- Easy to update and rollback
- Best for production

### Option 2: Direct Python
- Simple setup
- Full system access
- Requires manual dependency management
- Good for testing

### Option 3: Docker Compose
- Multi-service setup
- Persistent volumes
- Health checks included
- Best for complex setups

---

## 📋 Prerequisites

### VPS Requirements
- **OS**: Ubuntu 20.04+ / Debian 10+
- **CPU**: 2+ cores
- **RAM**: 4GB minimum (8GB recommended)
- **Storage**: 20GB+ (SSD recommended)
- **Network**: Stable internet connection

### Software Requirements
- Docker & Docker Compose (Option 1-3)
- OR Python 3.11+ (Option 2)
- Git

---

## 🐳 Option 1: Docker Deployment (Recommended)

### Step 1: SSH into VPS
```bash
ssh root@your_vps_ip
# Or with specific user
ssh username@your_vps_ip
```

### Step 2: Install Docker & Docker Compose
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt-get install -y docker-compose

# Verify installation
docker --version
docker-compose --version
```

### Step 3: Clone Project
```bash
cd /home/username
git clone https://github.com/yourusername/LLM-TradeBot.git
cd LLM-TradeBot
```

### Step 4: Create .env File
```bash
nano .env
```

Paste your configuration:
```dotenv
# Binance API
BINANCE_API_KEY=your_testnet_key
BINANCE_API_SECRET=your_testnet_secret
BINANCE_TESTNET=true

# LLM API
DEEPSEEK_API_KEY=your_deepseek_key
# OR
OPENAI_API_KEY=your_openai_key

# Trading Settings
TRADING_SYMBOLS=BTCUSDT
# Or AUTO3 for auto-selection
# TRADING_SYMBOLS=AUTO3
```

Save: `Ctrl+X` then `Y` then `Enter`

### Step 5: Build & Run Container
```bash
# Build image
docker build -t llm-tradebot .

# Run container
docker run -d \
  --name llm-tradebot \
  --restart unless-stopped \
  -p 8000:8000 \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  llm-tradebot
```

### Step 6: Monitor Container
```bash
# View logs
docker logs -f llm-tradebot

# Check status
docker ps | grep llm-tradebot

# Stop container
docker stop llm-tradebot

# Restart container
docker restart llm-tradebot
```

---

## 🐳 Option 3: Docker Compose (Full Stack)

### Step 1-3: Same as Option 1 above

### Step 4: Create .env File
```bash
cd LLM-TradeBot
nano .env
```

Paste same config as above.

### Step 5: Start Services
```bash
# Navigate to docker directory
cd docker

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f llm-tradebot

# Stop services
docker-compose down
```

### Step 6: Monitor
```bash
# Check service status
docker-compose ps

# View specific service logs
docker-compose logs -f llm-tradebot

# Execute commands in container
docker-compose exec llm-tradebot python simple_cli.py
```

---

## 🐍 Option 2: Direct Python Deployment

### Step 1: SSH into VPS
```bash
ssh username@your_vps_ip
```

### Step 2: Install System Dependencies
```bash
sudo apt-get update
sudo apt-get install -y \
  python3.11 \
  python3.11-venv \
  python3-pip \
  git \
  curl \
  build-essential
```

### Step 3: Clone Project
```bash
cd /home/username
git clone https://github.com/yourusername/LLM-TradeBot.git
cd LLM-TradeBot
```

### Step 4: Create Virtual Environment
```bash
python3.11 -m venv venv
source venv/bin/activate
```

### Step 5: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 6: Create .env File
```bash
nano .env
```

Paste configuration (same as Docker steps above).

### Step 7: Start Bot
```bash
# CLI Mode (Minimal)
python simple_cli.py

# Or with nohup for persistent running
nohup python simple_cli.py > logs/bot.log 2>&1 &
```

### Step 8: Monitor
```bash
# View live logs
tail -f logs/bot.log

# Check process
ps aux | grep python

# Kill process if needed
pkill -f "python simple_cli.py"
```

---

## 🔧 Configuration for Production

### Edit config.yaml
```bash
nano config.yaml
```

### For Testnet (Demo - First Time)
```yaml
binance:
  testnet: true  # ← Keep TRUE for demo
  api_key: "BINANCE_API_KEY"
  api_secret: "BINANCE_API_SECRET"
```

### For Live Trading (After Testing)
```yaml
binance:
  testnet: false  # ← Change to FALSE for live
```

### Risk Settings (Conservative for Production)
```yaml
risk:
  max_leverage: 3            # Lower than 5x
  max_total_position_pct: 20 # Lower than 30%
  max_consecutive_losses: 2  # Stop trading after losses
  stop_trading_on_drawdown_pct: 5  # Emergency stop
```

### Agent Settings
```yaml
agents:
  predict_agent: true
  regime_detector_agent: true
  trigger_detector_agent: true
  # Disable expensive LLM agents to save API costs
  trend_agent_llm: false
  setup_agent_llm: false
  trigger_agent_llm: false
```

---

## 📊 Access Dashboard

### Web Dashboard
After deployment, access at: `http://your_vps_ip:8000`

### SSH Tunneling (Secure Access)
```bash
# From your local machine
ssh -L 8000:localhost:8000 username@your_vps_ip
# Then access: http://localhost:8000
```

---

## 🔒 Security Best Practices

### 1. Firewall Configuration
```bash
# Allow SSH
sudo ufw allow 22/tcp

# Allow Web Dashboard
sudo ufw allow 8000/tcp

# Block everything else
sudo ufw default deny incoming
sudo ufw enable
```

### 2. API Key Security
- Store keys in `.env` only (never in config.yaml)
- `.env` should be git-ignored
- Use restricted API permissions (no withdrawal)
- Monitor API usage regularly

### 3. VPS Security
```bash
# Update system regularly
sudo apt-get update && sudo apt-get upgrade -y

# Set up SSH keys (no password login)
# Disable root login
# Enable firewall
# Consider fail2ban for brute-force protection
```

### 4. Process Monitoring
```bash
# Install supervisor for auto-restart
sudo apt-get install -y supervisor

# Create config file
sudo nano /etc/supervisor/conf.d/llm-tradebot.conf
```

Add:
```ini
[program:llm-tradebot]
directory=/home/username/LLM-TradeBot
command=/home/username/LLM-TradeBot/venv/bin/python simple_cli.py
autostart=true
autorestart=true
stderr_logfile=/var/log/llm-tradebot.err.log
stdout_logfile=/var/log/llm-tradebot.out.log
```

Then:
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start llm-tradebot
```

---

## 📝 Testing Before Production

### Step 1: Verify on Testnet First
```bash
# Keep testnet: true in config.yaml
# Run for 24-48 hours
# Monitor logs for errors
```

### Step 2: Check Logs
```bash
# View logs
tail -f logs/trading.log

# Look for:
# ✅ Consistent data fetching
# ✅ Agent decisions being made
# ✅ No connection errors
# ❌ Any ERROR messages
```

### Step 3: Monitor Resources
```bash
# Check CPU usage
top

# Check memory
free -h

# Check disk space
df -h
```

### Step 4: Backtest Strategy (Optional)
```bash
python backtest.py --start 2024-06-01 --end 2024-12-31 --symbol BTCUSDT
```

### Step 5: Switch to Live (After Confidence)
Edit `config.yaml`:
```yaml
binance:
  testnet: false  # ← Change to live
```

Restart bot:
```bash
# Docker
docker restart llm-tradebot

# Direct Python - stop old process
pkill -f "python simple_cli.py"
# Start new one
nohup python simple_cli.py > logs/bot.log 2>&1 &
```

---

## 🚨 Troubleshooting

### Bot Won't Start
```bash
# Check logs
docker logs llm-tradebot
# OR
tail -f logs/bot.log

# Common issues:
# 1. Missing .env file
# 2. Invalid API keys
# 3. Python not installed
# 4. Port 8000 already in use
```

### Connection Errors
```bash
# Test Binance connectivity
curl -I https://api.binance.com

# Check if testnet URL is accessible
curl -I https://testnet.binancefuture.com
```

### High Memory Usage
```bash
# Check memory
free -h

# Restart container/process
docker restart llm-tradebot
# OR
pkill -f python; sleep 2; python simple_cli.py &
```

### API Rate Limit Issues
```bash
# Check logs for rate limit errors
grep "429" logs/trading.log

# Solution: Reduce trading frequency in config.yaml
```

---

## 📊 Monitoring Setup

### View Real-Time Logs
```bash
# Docker
docker logs -f llm-tradebot

# Direct Python
tail -f logs/trading.log
```

### Set Up Log Alerts
```bash
# Monitor for errors
grep ERROR logs/trading.log

# Count errors in last hour
grep "$(date +'%Y-%m-%d %H' --date='1 hour ago')" logs/trading.log | grep ERROR
```

### Health Check
```bash
# Check if bot is responding
curl http://your_vps_ip:8000

# Should return dashboard or API response
```

---

## 🔄 Maintenance

### Update Bot Code
```bash
cd ~/LLM-TradeBot
git pull origin main

# Rebuild Docker image
docker build -t llm-tradebot .
docker restart llm-tradebot

# Or reinstall dependencies for direct Python
source venv/bin/activate
pip install -r requirements.txt
```

### Backup Important Data
```bash
# Backup logs
tar -czf logs_backup_$(date +%Y%m%d).tar.gz logs/

# Backup data
tar -czf data_backup_$(date +%Y%m%d).tar.gz data/

# Upload to cloud storage
scp logs_backup_*.tar.gz username@backup_server:/backups/
```

### Rotate Logs
```bash
# Set up logrotate
sudo nano /etc/logrotate.d/llm-tradebot
```

Add:
```
/home/username/LLM-TradeBot/logs/*.log {
    daily
    rotate 10
    compress
    delaycompress
    missingok
    notifempty
}
```

---

## ✅ Production Checklist

- [ ] VPS provisioned with required specs
- [ ] Docker/Python installed
- [ ] Project cloned
- [ ] .env file created with API keys
- [ ] config.yaml configured
- [ ] Testnet verified (24-48 hours)
- [ ] Logs monitored for errors
- [ ] Firewall configured
- [ ] API permissions restricted
- [ ] Monitoring/alerting set up
- [ ] Backup strategy implemented
- [ ] Ready for live trading

---

## 🎉 Deployment Complete!

Your bot is now running 24/7 on the VPS. Monitor it regularly and adjust settings as needed.

For help: Check logs first, then review this guide.
