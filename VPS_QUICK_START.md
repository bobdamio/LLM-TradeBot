# 🚀 VPS Deployment - Quick Reference

## 3 Deployment Methods

### 🐳 **Option 1: Docker (5 mins - RECOMMENDED)**
```bash
# SSH to VPS
ssh root@your_vps_ip

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh

# Clone project
git clone <repo-url> && cd LLM-TradeBot

# Create .env with your API keys
cat > .env << EOF
BINANCE_API_KEY=your_key
BINANCE_API_SECRET=your_secret
BINANCE_TESTNET=true
DEEPSEEK_API_KEY=your_llm_key
TRADING_SYMBOLS=BTCUSDT
EOF

# Build & run
docker build -t llm-tradebot .
docker run -d --name llm-tradebot --restart unless-stopped -p 8000:8000 --env-file .env -v $(pwd)/data:/app/data -v $(pwd)/logs:/app/logs llm-tradebot

# Monitor
docker logs -f llm-tradebot
```

### 🐳 **Option 2: Docker Compose (3 mins)**
```bash
cd docker
docker-compose up -d
docker-compose logs -f llm-tradebot
```

### 🐍 **Option 3: Direct Python (10 mins)**
```bash
# Install Python 3.11+
sudo apt-get install -y python3.11-venv python3-pip git

# Setup project
git clone <repo-url> && cd LLM-TradeBot
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create .env
nano .env  # Add API keys

# Run bot
python simple_cli.py
# OR for persistent:
nohup python simple_cli.py > logs/bot.log 2>&1 &
```

---

## ✅ Essential Configuration

### .env File (All Options)
```dotenv
BINANCE_API_KEY=your_testnet_key
BINANCE_API_SECRET=your_testnet_secret
BINANCE_TESTNET=true
DEEPSEEK_API_KEY=your_llm_key
TRADING_SYMBOLS=BTCUSDT
```

### config.yaml Updates
```yaml
# For TESTNET (Demo)
binance:
  testnet: true

# For LIVE (After testing)
binance:
  testnet: false

# Conservative risk settings
risk:
  max_leverage: 3
  max_total_position_pct: 20
  max_consecutive_losses: 2
```

---

## 📊 Monitoring

```bash
# Docker
docker logs -f llm-tradebot         # Live logs
docker ps | grep llm-tradebot       # Check status
docker restart llm-tradebot         # Restart

# Direct Python
tail -f logs/bot.log                # Live logs
ps aux | grep python                # Check process
pkill -f "python simple_cli.py"     # Kill process
```

---

## 🔒 Security

```bash
# Firewall
sudo ufw allow 22,8000/tcp
sudo ufw enable

# API security
# 1. Use testnet keys first
# 2. Restrict IP whitelist on Binance
# 3. Disable withdrawal permissions
# 4. Monitor API usage
```

---

## 🧪 Testing Workflow

1. **Deploy on testnet** → `BINANCE_TESTNET=true`
2. **Monitor 24-48 hours** → Watch logs, check signals
3. **Verify logs** → No errors, signals generating
4. **Backtest** → `python backtest.py --symbol BTCUSDT`
5. **Switch to live** → `BINANCE_TESTNET=false` (if confident)
6. **Monitor again** → First 48 hours intensively

---

## 📈 VPS Requirements

| Spec | Minimum | Recommended |
|------|---------|-------------|
| CPU | 2 cores | 4 cores |
| RAM | 4GB | 8GB |
| Storage | 20GB | 50GB SSD |
| Bandwidth | Unlimited | Stable |

---

## ❓ Common Issues

| Issue | Solution |
|-------|----------|
| "Connection refused" | Check .env file, verify API keys |
| "Port 8000 in use" | Change port in config or kill process |
| "High memory" | Restart container/process |
| "Rate limit 429" | Reduce trading frequency |

---

## 📚 Full Guide

See **VPS_DEPLOYMENT.md** for complete setup with:
- Detailed step-by-step instructions
- Full troubleshooting guide
- Security best practices
- Monitoring setup
- Production checklist

---

## 🚀 Ready?

**Choose your deployment method above and follow the commands!**

Questions? Check VPS_DEPLOYMENT.md or bot logs.
