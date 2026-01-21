# GitHub Copilot Instructions

## Architecture Overview
This project is designed for automated trading with a focus on minimal footprint and production readiness. Key features include:
- **Minimal footprint**: Only core trading components are loaded.
- **Production-ready**: Designed for stable 24/7 operation.
- **AUTO3 support**: Automatic best symbol selection via backtest.
- **LLM integration**: Full multi-agent decision system.
- **Risk management**: Built-in risk audit and position limits.
- **Graceful shutdown**: Use Ctrl+C for a clean exit.

## Project Structure
Key directories:
- `src/agents/`: Multi-agent system components (DataSyncAgent, QuantAnalystAgent, DecisionCoreAgent, RiskAuditAgent)
- `src/api/`: Binance client and WebSocket implementations
- `src/execution/`: Trade execution engine
- `src/risk/`: Risk management and auditing
- `src/strategy/`: Strategy and signal processing
- `src/data/`: Market data processing
- `tests/`: Comprehensive test suite for agents and strategies

## Installation & Setup

### Step 1: Installation
Run the installation script to set up the Python environment:
```bash
chmod +x install.sh
./install.sh
```

This script:
- Checks Python version (requires 3.11+)
- Creates a virtual environment
- Installs dependencies from requirements.txt
- Validates the installation

### Step 2: Configure API Keys
Edit the `.env` file with your credentials (or use the setup script below):

### Step 3: Use Setup Script (Optional)
```bash
chmod +x set_api_keys.sh
source set_api_keys.sh
```

### Step 4: Verify Production Setup
Run verification before live trading:
```bash
python verify_production_setup.py
```

## Starting the Bot

### Option 1: Simple CLI Mode (Minimal Footprint) - RECOMMENDED
Fastest startup with core trading only:
```bash
python simple_cli.py
```

This is the recommended way to start. It:
- Loads only essential components
- Supports AUTO3 symbol selection
- Integrates with the full multi-agent system
- Provides real-time trading decisions

### Option 2: Full Bot with Web Dashboard
Start the bot with web UI for monitoring:
```bash
chmod +x start.sh
./start.sh
```

The `start.sh` script:
- Activates the virtual environment
- Validates `.env` configuration
- Checks required environment variables
- Starts the main trading loop with web dashboard
- Provides graceful Ctrl+C shutdown

### Option 3: Switch to Production Environment
Configure Binance production environment:
```bash
chmod +x switch_to_production.sh
./switch_to_production.sh
```

The `switch_to_production.sh` script performs the following steps:

**Step 1: Environment Check**
- Verifies `config.yaml` exists (copies from `config.example.yaml` if needed)
- Verifies `.env` file exists (creates from `.env.example` if missing)
- Checks Python 3 installation

**Step 2: Configure API Keys**
- Prompts for Binance API Key and Secret
- Validates and writes credentials to `.env` file
- Saves in secure environment variables

**Step 3: Switch to Production**
- Creates backup of `config.yaml` to `config.yaml.backup`
- Changes `testnet: true` to `testnet: false` in config
- Enables real market data and live account access

**Step 4: Connection Test**
- Runs `test_binance_connection.py` to verify API connectivity
- Checks for common issues (invalid keys, insufficient permissions, IP whitelist, network)
- Reports test results

**Step 5: Summary**
- Provides next steps for data validation
- Shows rollback instructions if needed
- Displays security reminders

**Important Notes:**
- ✅ Creates automatic backup before switching environments
- ✅ Can rollback to testnet: `sed -i '' 's/testnet: false/testnet: true/' config.yaml`
- ✅ Verify with: `python show_data_pipeline.py`
- ⚠️ Never share API keys
- ⚠️ Start with small amounts to test live trading

## Backtesting & Optimization

### Basic Backtest
Test a strategy on historical data:
```bash
python backtest.py --start 2024-01-01 --end 2024-12-31 --symbol BTCUSDT
```

### Backtest with AUTO3 (Auto Symbol Selection)
Let the system select the best trading pair:
```bash
python backtest.py --start 2024-01-01 --end 2024-12-31 --symbol AUTO3
```

### Backtest with Custom Parameters
```bash
python backtest.py \
  --start 2024-06-01 \
  --end 2024-12-31 \
  --symbol ETHUSDT \
  --capital 50000 \
  --step 12
```
Where `--step` is: 1=5min, 3=15min, 12=1hr

### Multi-Symbol Backtest
Test across multiple symbols:
```bash
python run_multi_symbol_backtest.py
```

### Optimize Strategy Parameters
Find optimal parameters via backtesting:
```bash
python optimize_backtest.py
```

### Compare Strategies
Compare different strategy approaches:
```bash
python compare_strategies.py
```

## Environment Variables

### Required for Live Trading
```bash
BINANCE_API_KEY          # Binance Futures API Key
BINANCE_API_SECRET       # Binance Futures Secret
TRADING_SYMBOLS          # Trading pairs: "BTCUSDT,ETHUSDT" or "AUTO3"
```

### LLM Integration (Choose one)
```bash
DEEPSEEK_API_KEY         # DeepSeek API key (recommended)
OPENAI_API_KEY           # OpenAI API key (alternative)
```

### Optional Configuration
```bash
USE_WEBSOCKET=false      # Use REST API (default) or WebSocket
ENABLE_DETAILED_LLM_LOGS=true  # Enable detailed logging for local dev
DEPLOYMENT_MODE=local    # "local" or "railway"
```

## Multi-Agent System

### Agent Hierarchy
1. **DataSyncAgent**: Collects market data concurrently
2. **QuantAnalystAgent**: Generates quantitative signals
3. **DecisionCoreAgent**: Applies weighted voting algorithm
4. **RiskAuditAgent**: Executes risk checks (veto power)

### Agent Features
- Async concurrent execution (reduces 60% wait time)
- Dual-view data structure (stable + live)
- Layered signal analysis (trend + oscillator)
- Multi-timeframe decision alignment
- Automatic stop-loss direction correction
- Risk veto mechanism

## Risk Management
- Position limits enforced by RiskAuditAgent
- Stop-loss automatically adjusted
- Margin requirements validated
- Account health monitored continuously

## Monitoring & Logs
- Web dashboard available at `http://localhost:8000` (when using `start.sh`)
- Trading logs saved in configured output directory
- Real-time terminal output shows agent decisions
- Detailed agent logs available in `logs/` directory

## Configuration
The trading symbols are read from the `.env` file. Here's how to set it up:
```bash
# Binance Futures API
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here

# LLM Provider (DeepSeek or OpenAI)
DEEPSEEK_API_KEY=your_deepseek_key_here
# OR
OPENAI_API_KEY=your_openai_key_here

# Trading Configuration
TRADING_SYMBOLS=BTCUSDT,ETHUSDT
# Or use AUTO3 for automatic best symbol selection
TRADING_SYMBOLS=AUTO3
```

## Live Trading Prerequisites
Before starting live trading, ensure:
- ✅ Valid Binance Futures API keys in `.env`
- ✅ Sufficient USDT balance in Futures wallet
- ✅ API permissions: Read + Futures Trading enabled
- ✅ DeepSeek/OpenAI API key configured
- ✅ Run `verify_production_setup.py` to validate

## Graceful Shutdown
To safely stop the bot:
```bash
# Press Ctrl+C in the terminal
Ctrl+C
```

This will:
- Close all open positions gracefully
- Save trading logs and state
- Clean up connections
- Exit safely

## Switching Back to Testnet (Rollback)
If you need to revert from production to testnet:
```bash
# Option 1: Restore from backup
mv config.yaml.backup config.yaml

# Option 2: Manual rollback
sed -i '' 's/testnet: false/testnet: true/' config.yaml
```

After rollback, verify the change:
```bash
grep "testnet:" config.yaml
```

## Verification & Testing

### Test Binance Connection
Verify API connectivity before trading:
```bash
python test_binance_connection.py
```

### Verify Data Pipeline
Check data quality and alignment:
```bash
python show_data_pipeline.py
```



```bash
# Start live trading
python main.py --mode continuous
```

> **WARNING**: This mode executes real trades on Binance Futures!