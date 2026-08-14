# Conformance Technical Specification and Server / GPU Deployment Guide

This guide provides the complete engineering specification of the four governance layers, database configuration, and step-by-step deployment instructions for bare-metal Linux servers and GPU workstations.

---

## 1. Governance Engine Technical Specification

### Layer 1: Sub-15ms Deterministic PII and Secret Tokenizer
The deterministic engine executes on local CPU without sending sensitive data to external networks.

#### Detection Mechanics:
* Pattern Recognition: High-speed compiled regular expressions identifying US SSNs, email addresses, phone numbers, corporate employee IDs (EMP-XXXXXX), medical record numbers (MRN), and developer API tokens (sk-, ghp-, AKIA).
* Mathematical Checksums: Luhn Checksum validation prevents false positives on 16-digit credit cards.
* Lexical Context: Contextual word windows detect confidential or proprietary markers.
* Execution Latency: 0.18ms to 1.05ms per transaction on standard CPU.

---

### Layer 2: Adversarial Injection and Jailbreak Guard
Protects against prompt hijacking, credential extraction, and delimiter abuse.

#### Detection Mechanics:
* Delimiter escaping checks and recursive instruction override detection.
* Role-play adversarial classifiers (detecting DAN, system prompt extraction, developer mode exploits).
* Latency: Sub-1ms execution.

---

### Layer 3: Multi-SLM Profile-as-Jury Panel (Local AI Layer)
Rather than relying on a single general cloud model, Conformance deploys a panel of three on-premise Small Language Models (SLMs).

#### Panel Composition:
* Microsoft Phi-4 Mini (3.8B): EU AI Act Article 26 Judge evaluating Annex III recruitment/credit risk, transparency, and bias.
* Mistral 7B Instruct: GDPR Sovereignty Judge evaluating data minimization and cross-border transfer constraints (GDPR Art. 44).
* Google Gemma 3 (4B): ANSSI AI Security Judge evaluating prompt injections and tool abuse.

#### Epistemic Consensus and Regulatory Uncertainty Signal (U):
The jury calculates the uncertainty metric across the three models:
`U = 1 - 2 * |P(Compliant) - 0.5|`
* U <= 0.10: High consensus. Request approved.
* U >= 0.35: Significant inter-model divergence. Request is automatically quarantined and forwarded to the Human Compliance Officer Queue (EU AI Act Article 26(2) mandate).

---

### Layer 4: Knowledge Graph Hallucination Verifier
Validates model output against deterministic semantic entity triples (Subject -> Predicate -> Object) to detect factual drift before responses reach end users.

---

## 2. Production Server and GPU Deployment Guide

This section covers deploying Conformance on a dedicated GPU server (AWS EC2 g5.xlarge / G4dn, RunPod, Lambda Labs, or On-Premise NVIDIA RTX / A100 / H100).

### Hardware Requirements
* Minimum CPU Deployment: 4 vCPU, 8 GB RAM, 20 GB SSD.
* Recommended GPU Deployment (Multi-SLM Local Inference):
  * GPU: 1x NVIDIA A10G (24GB VRAM) or RTX 4090 / A5000 / A100.
  * RAM: 32 GB System RAM.
  * Storage: 100 GB NVMe SSD.

---

### Step 1: System and NVIDIA Driver Setup (Ubuntu 22.04 / 24.04 LTS)

```bash
# Update packages
sudo apt update && sudo apt upgrade -y

# Install build dependencies and Python
sudo apt install -y build-essential curl git python3-pip python3-venv

# Install NVIDIA CUDA Drivers (if using GPU)
sudo apt install -y nvidia-driver-535 nvidia-utils-535
sudo apt install -y nvidia-cuda-toolkit

# Verify GPU availability
nvidia-smi
```

---

### Step 2: Install and Configure Local SLM Server (Ollama / vLLM on GPU)

Run the local model server to host the three specialized SLM jury models:

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull the three specialized SLM models
ollama pull phi4-mini
ollama pull mistral:7b
ollama pull gemma3:4b

# Verify models are running on GPU
ollama list
```

---

### Step 3: Production Database Setup (PostgreSQL)

For high-throughput enterprise deployments (10,000+ spans/minute), connect Conformance to PostgreSQL:

```bash
# Install PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql -c "CREATE DATABASE conformance_db;"
sudo -u postgres psql -c "CREATE USER conformance_user WITH ENCRYPTED PASSWORD 'StrongSecurePassword123!';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE conformance_db TO conformance_user;"
```

Set the database connection in your environment:
```bash
export DATABASE_URL="postgresql://conformance_user:StrongSecurePassword123!@localhost:5432/conformance_db"
```

---

### Step 4: Deploying Conformance Backend and Frontend

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/continuous-ai-governance.git
cd continuous-ai-governance

# 1. Setup Backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start backend with 4 production Uvicorn workers
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 &

# 2. Setup Frontend
cd ../frontend
npm install
npm run build

# Serve frontend using Nginx or Node
sudo apt install -y nginx
sudo cp -r dist/* /var/www/html/
```

---

## 3. Production Docker Compose Stack (1-Command GPU Launch)

You can run the entire stack (FastAPI Gateway + PostgreSQL + Ollama GPU + Frontend) with Docker Compose:

### `docker-compose.yml`
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: conformance-postgres
    restart: always
    environment:
      POSTGRES_DB: conformance_db
      POSTGRES_USER: conformance_user
      POSTGRES_PASSWORD: StrongPassword123!
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  ollama-gpu:
    image: ollama/ollama:latest
    container_name: conformance-ollama
    restart: always
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: conformance-backend
    restart: always
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://conformance_user:StrongPassword123!@postgres:5432/conformance_db
      - UPSTREAM_OPENAI_URL=http://ollama-gpu:11434/v1
    depends_on:
      - postgres
      - ollama-gpu

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: conformance-frontend
    restart: always
    ports:
      - "80:80"
    depends_on:
      - backend

volumes:
  pgdata:
  ollama_data:
```

### Launching the Stack:
```bash
docker compose up -d
```
* The control center will be available at `http://YOUR_SERVER_IP`
* The OpenAI proxy will be available at `http://YOUR_SERVER_IP:8000/v1`

---

## 4. Demonstrating the Platform to Stakeholders

When presenting Conformance to executive stakeholders or compliance auditors:

1. Live Interception:
   Send an unredacted prompt containing credit cards or patient IDs to port 8000. Show how Presidio masks the sensitive data before it reaches the model in under 1 millisecond.
2. Signal Feed and Human Review Queue:
   Open the Signal Feed tab on the dashboard. Show how the committee action radio selectors allow Data Protection Officers to triage high-risk usage.
3. Cryptographic GAAT Ledger Verification:
   Navigate to the Audit Vault tab. Click "Verify Hash Chain" to demonstrate mathematically intact SHA-256 evidence satisfying EU AI Act Article 26(6).
4. Knowledge Graph Fact Checking:
   Navigate to the Knowledge Graph tab. Click "Test Hallucinated Output" to demonstrate how the system catches factual contradictions.
