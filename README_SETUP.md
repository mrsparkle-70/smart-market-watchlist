# Smart Market Watchlist — Setup Guide

Complete setup instructions for running the project on **Windows**, **macOS**, or **Linux**.

---

## Table of Contents

1. [Windows Setup (Quick Start)](#windows-setup-quick-start)
2. [Windows Full Setup](#windows-full-setup)
3. [macOS/Linux Setup](#macoslinux-setup)
4. [Docker Setup (All Platforms)](#docker-setup-all-platforms)
5. [Environment Variables](#environment-variables)
6. [Verifying the Setup](#verifying-the-setup)
7. [Running Tests](#running-tests)
8. [Common Issues & Troubleshooting](#common-issues--troubleshooting)
9. [Switching to Real Market Data](#switching-to-real-market-data)
10. [Optional: Enabling LLM Explanations](#optional-enabling-llm-explanations)

---

## Windows Setup (Quick Start)

### Prerequisites

| Requirement | Version | Download |
|-------------|---------|----------|
| **Python** | 3.9+ | [python.org/downloads](https://www.python.org/downloads/) |
| **Node.js** | 18+ | [nodejs.org](https://nodejs.org/) |
| **Git** | Any | [git-scm.com](https://git-scm.com/) |

> **Important**: During Python installation, check **"Add Python to PATH"** at the bottom of the installer.

### Quick Start Commands (Windows PowerShell)

```powershell
# 1. Clone the repository
git clone <your-repo-url>
cd smart-market-watchlist

# 2. Start the backend (Terminal 1)
cd apps\api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 3. Start the frontend (Terminal 2 - New PowerShell window)
cd apps\web
npm install
npm run dev

# 4. Open http://localhost:3000 in your browser
```

---

## Windows Full Setup

### Step 1: Install Prerequisites

#### 1.1 Install Python

1. Download Python from [python.org/downloads](https://www.python.org/downloads/)
2. Run the installer
3. **Check "Add Python to PATH"** at the bottom of the installer
4. Click "Install Now"

Verify installation:
```powershell
python --version
# Expected: Python 3.9.x or higher
```

#### 1.2 Install Node.js

1. Download Node.js 18+ from [nodejs.org](https://nodejs.org/)
2. Run the installer with default settings

Verify installation:
```powershell
node --version
# Expected: v18.x.x or higher

npm --version
# Expected: 9.x.x or higher
```

#### 1.3 Install Git

1. Download Git from [git-scm.com](https://git-scm.com/)
2. Run the installer with default settings

Verify installation:
```powershell
git --version
# Expected: git version 2.x.x or higher
```

### Step 2: Clone the Repository

```powershell
git clone <your-repo-url>
cd smart-market-watchlist
```

### Step 3: Backend Setup (FastAPI)

Open **PowerShell** and run:

```powershell
# Navigate to the API directory
cd apps\api

# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# If you get a security error, run this first:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Install dependencies
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables

```powershell
# Copy the example environment file
copy ..\.env.example ..\.env

# Or create .env manually with this content:
@"
# --- App ---
ENV=development
CORS_ORIGINS=http://localhost:3000

# --- Persistence ---
DATABASE_URL=sqlite:///./watchlist.db
REDIS_URL=

# --- Auth ---
JWT_SECRET=your-secret-key-change-this

# --- Market data provider ---
MARKET_DATA_PROVIDER=mock
MARKET_DATA_API_KEY=
BENCHMARK_SYMBOL=SPY

# --- Background pipeline ---
POLL_INTERVAL_SECONDS=300
PIPELINE_ENABLED=true

---

## Windows Commands Reference

### Virtual Environment

| Command | macOS/Linux | Windows PowerShell |
|---------|-------------|-------------------|
| Create | `python3 -m venv .venv` | `python -m venv .venv` |
| Activate | `source .venv/bin/activate` | `.\.venv\Scripts\Activate.ps1` |
| Deactivate | `deactivate` | `deactivate` |

### Directory Navigation

| Command | macOS/Linux | Windows |
|---------|-------------|---------|
| List files | `ls` | `dir` or `ls` |
| Change directory | `cd apps/api` | `cd apps\api` |
| Copy file | `cp source dest` | `copy source dest` |
| Create directory | `mkdir folder` | `mkdir folder` |

### Process Management

| Command | macOS/Linux | Windows PowerShell |
|---------|-------------|-------------------|
| Find process on port | `lsof -i :8000` | `netstat -ano \| findstr :8000` |
| Kill process | `kill -9 <PID>` | `taskkill /PID <PID> /F` |
| List processes | `ps aux` | `Get-Process` |

### Troubleshooting Windows Issues

**PowerShell Execution Policy Error:**
```powershell
# If you get "running scripts is disabled" error:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Then try activating again:
.\.venv\Scripts\Activate.ps1
```

**Port Already in Use:**
```powershell
# Find process using port 8000
netstat -ano | findstr :8000

# Kill the process (replace <PID> with actual PID)
taskkill /PID <PID> /F
```

**Python Not Found:**
```powershell
# If python command doesn't work, try:
py --version

# Or use full path:
C:\Python311\python.exe --version
```

---

## macOS/Linux Setup

### Quick Start (macOS/Linux Terminal)

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd smart-market-watchlist


---

## Verifying the Setup

### Backend Verification

**Windows PowerShell:**
```powershell
# Health check
Invoke-RestMethod -Uri "http://localhost:8000/api/health"
# Expected: {"status":"ok","provider":"mock"}

# Or use browser
Start-Process "http://localhost:8000/api/docs"
```

**macOS/Linux:**
```bash
curl http://localhost:8000/api/health
# Expected: {"status":"ok","provider":"mock"}
```

### Frontend Verification

Open browser: http://localhost:3000

---

## Running Tests

### Local Testing

**Windows PowerShell:**
```powershell
# Navigate to API directory
cd apps\api

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Run all tests
python -m pytest tests/ -q

# Run with verbose output
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_features.py -v
```

**macOS/Linux:**
```bash
cd apps/api
source .venv/bin/activate
python -m pytest tests/ -q
```

### Docker Testing

```bash
docker compose exec api python -m pytest tests/ -q
```

### Test Coverage

| Test File | Tests | Coverage Area |
|-----------|-------|---------------|
| `test_features.py` | 8 | Pure feature calculations |
| `test_attention.py` | 6 | Scoring system |
| `test_change_detection.py` | 7 | Event detection |
| `test_api_flow.py` | 8 | End-to-end API flow |
| **Total** | **29** | Features, scoring, detection, auth, watchlists, E2E |

---

## Common Issues & Troubleshooting

### Windows-Specific Issues

**PowerShell Execution Policy:**
```powershell
# Error: "running scripts is disabled on this system"
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Python Not Found:**
```powershell
# Try these alternatives:
py --version
python3 --version
where python
```

**Port Already in Use:**
```powershell
# Windows PowerShell
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

**Node.js Build Errors:**
```powershell
# Clear npm cache
npm cache clean --force
rm node_modules
rm package-lock.json
npm install
```

### macOS/Linux Issues

**Port Already in Use:**
```bash
lsof -i :8000
kill -9 <PID>
```

**Permission Denied:**
```bash
chmod +x .venv/bin/activate
```

### General Issues

**CORS Errors:**
- Ensure `CORS_ORIGINS` includes `http://localhost:3000`
- Restart the backend after changing .env

**Module Not Found:**
```bash
# Make sure virtual environment is activated
# Make sure you're in the apps/api directory
pip install -r requirements.txt
```

**Frontend Can't Connect to Backend:**
- Ensure backend is running on port 8000
- Check `API_PROXY_URL` in environment

---

## Switching to Real Market Data

### Using Finnhub

1. Get a free API key from [finnhub.io](https://finnhub.io/)
2. Edit `.env` file:
   ```env
   MARKET_DATA_PROVIDER=finnhub
   MARKET_DATA_API_KEY=your-key-here
   ```
3. Restart the backend

### Finnhub API Limits

| Plan | Rate Limit |
|------|-----------|
| **Free** | 60 calls/minute |
| **Startup** | 120 calls/minute |
| **Developer** | 3600 calls/minute |

---

## Optional: Enabling LLM Explanations

1. Get API key from [console.groq.com](https://console.groq.com/) (free)
2. Edit `.env` file:
   ```env
   LLM_API_KEY=your-groq-key
   LLM_BASE_URL=https://api.groq.com/openai/v1
   LLM_MODEL=openai/gpt-oss-20b
   ```
3. Restart the backend

> **Note**: App works fully without LLM. Deterministic templates are used by default.

---

## Summary

### Windows Quick Start

```powershell
# Backend (Terminal 1)
cd apps\api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (Terminal 2)
cd apps\web
npm install
npm run dev

# Open http://localhost:3000
```

### macOS/Linux Quick Start

```bash
# Backend (Terminal 1)
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (Terminal 2)
cd apps/web
npm install
npm run dev

# Open http://localhost:3000
```

### Docker (All Platforms)

```bash
docker compose up --build -d
# Open http://localhost:3000
```

# 2. Start the backend (Terminal 1)
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 3. Start the frontend (Terminal 2)
cd apps/web
npm install
npm run dev

# 4. Open http://localhost:3000 in your browser
```

---

## Docker Setup (All Platforms)

### Install Docker Desktop

1. Download Docker Desktop from [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/)
2. Install and restart your computer
3. Open Docker Desktop and wait for it to start

### Run with Docker

```bash
# Clone the repository
git clone <your-repo-url>
cd smart-market-watchlist

# Copy environment file
cp .env.example .env

# Build and start all services
docker compose up --build -d

# Open http://localhost:3000 in your browser
```

### Docker Commands

| Command | Description |
|---------|-------------|
| `docker compose up --build -d` | Build and start all services |
| `docker compose logs -f` | View all logs |
| `docker compose ps` | List running containers |
| `docker compose down` | Stop all services |
| `docker compose down -v` | Stop and remove all data |
| `docker compose exec api python -m pytest tests/ -q` | Run tests |

---

## Environment Variables

### Complete Reference

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `ENV` | `development` | No | Environment: `development` or `production` |
| `CORS_ORIGINS` | `http://localhost:3000` | No | Comma-separated allowed origins |
| `DATABASE_URL` | `sqlite:///./watchlist.db` | No | Database connection string |
| `REDIS_URL` | (empty) | No | Redis connection string |
| `JWT_SECRET` | `dev-secret-change-me` | Yes (production) | JWT signing secret |
| `MARKET_DATA_PROVIDER` | `mock` | No | Provider: `mock` or `finnhub` |
| `MARKET_DATA_API_KEY` | (empty) | If using Finnhub | Finnhub API key |
| `MARKET_DATA_BASE_URL` | (empty) | No | Custom provider base URL |
| `BENCHMARK_SYMBOL` | `SPY` | No | Benchmark for relative performance |
| `POLL_INTERVAL_SECONDS` | `300` | No | Pipeline polling interval (seconds) |
| `PIPELINE_ENABLED` | `true` | No | Enable background pipeline |
| `LLM_API_KEY` | (empty) | No | OpenAI/Groq API key for explanations |
| `LLM_BASE_URL` | `https://api.groq.com/openai/v1` | No | LLM API base URL |
| `LLM_MODEL` | `openai/gpt-oss-20b` | No | LLM model name |
| `API_PROXY_URL` | `http://localhost:8000` | No | Frontend API proxy URL |

### Generating a Secure JWT Secret

**Windows PowerShell:**
```powershell
# Generate a random secret
-join ((65..90) + (97..122) + (48..57) + (35, 36, 37, 38, 42, 43, 45, 95) | Get-Random -Count 64 | ForEach-Object {[char]$_})
```

**macOS/Linux:**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```


# --- Optional LLM ---
LLM_API_KEY=
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=openai/gpt-oss-20b

# --- Frontend ---
API_PROXY_URL=http://localhost:8000
"@ | Out-File -FilePath "..\env" -Encoding utf8
```

### Step 5: Run the Backend

```powershell
# Make sure virtual environment is activated
.\.venv\Scripts\Activate.ps1

# Run with auto-reload (recommended for development)
uvicorn app.main:app --reload --port 8000

# Or run without auto-reload
uvicorn app.main:app --port 8000
```

### Step 6: Frontend Setup (Next.js)

Open a **new PowerShell** window and run:

```powershell
# Navigate to the web directory
cd apps\web

# Install dependencies
npm install
```

### Step 7: Run the Frontend

```powershell
# Make sure you're in the apps\web directory
cd apps\web

# Run development server
npm run dev
```

### Step 8: First-Time Setup in the Browser

1. Open http://localhost:3000 in your browser
2. Register a new account
3. Add symbols (AAPL, NVDA, MSFT, TSLA)
4. Click "Refresh market data" to establish a baseline
5. Explore your personalized change brief
