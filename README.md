Yes — the README currently only covers phases 1-6. Let's update it to reflect everything you've built. Open `README.md` and replace the entire contents with this:

```markdown
# Auth System

A production-style authentication system built with FastAPI, as a learn-by-doing project. Built incrementally, phase by phase, to deeply understand each concept rather than copy-pasting a finished solution.

## Features

- **Signup/Login** — passwords hashed with bcrypt, never stored in plain text
- **JWT authentication** — stateless access tokens, protected routes via FastAPI dependency injection
- **Redis caching** — cache-first login flow, falls back to MongoDB on cache miss
- **Rate limiting** — brute-force protection on login (5 requests/minute per IP)
- **OTP email verification** — signup triggers a background Celery task that emails a 6-digit code, expiring in 5 minutes
- **Refresh tokens** — long-lived (7-day) tokens that exchange for new short-lived access tokens
- **Bloom filters** — probabilistic duplicate email detection, avoids unnecessary DB lookups on signup
- **Kafka batch writes** — signups publish to a Kafka topic instead of writing directly to MongoDB; a consumer accumulates messages and bulk inserts in batches of 100
- **Write-through caching** — user data written to Redis immediately on signup, so login works even before the Kafka consumer flushes to MongoDB

## Tech Stack

- **FastAPI** — web framework
- **MongoDB** (via Motor) — persistent user storage
- **Redis** — caching, OTP storage, refresh token storage, rate limiting, Celery broker, Kafka offset tracking
- **Kafka** — event streaming for decoupled, batched DB writes
- **Celery** — background task processing (OTP emails)
- **bcrypt** — password hashing
- **python-jose** — JWT creation and verification
- **slowapi** — rate limiting
- **kafka-python** — Kafka producer/consumer client

## Project Structure

```
auth-system/
├── main.py                   # FastAPI app entrypoint
├── celery_app.py             # Celery configuration
├── kafka_consumer.py         # Standalone Kafka consumer (batch DB writer)
├── routes/
│   └── auth.py               # All auth endpoints
├── models/
│   └── user.py               # Pydantic request models
├── db/
│   ├── mongo.py              # MongoDB connection
│   └── redis_client.py       # Redis connection
├── utils/
│   ├── jwt_handler.py        # Token creation/verification, auth dependency
│   ├── limiter.py            # Rate limiter config
│   ├── otp.py                # OTP generation
│   ├── kafka_producer.py     # Kafka producer singleton
│   ├── bloom_filter.py       # Bloom filter implementation
│   └── bloom_filter_instance.py  # Shared bloom filter instance
├── tasks/
│   └── email_tasks.py        # Celery task for sending OTP emails
├── .env.example
├── .gitignore
└── requirements.txt
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/signup` | Register a new user, sends OTP email, publishes to Kafka |
| POST | `/auth/login` | Authenticate, returns access + refresh tokens |
| POST | `/auth/verify-otp` | Verify email using the OTP code |
| POST | `/auth/refresh` | Exchange a refresh token for a new access token |
| GET | `/auth/me` | Get the current authenticated user (requires Bearer token) |

## Setup

### Prerequisites

- Python 3.11+
- MongoDB (`brew install mongodb-community`)
- Redis (`brew install redis`)
- Kafka + ZooKeeper (`brew install kafka`)
- Java 17+ (`brew install openjdk@17`) — required by Kafka

### Installation

```bash
git clone https://github.com/AdityaWaghmare2004/auth-system.git
cd auth-system
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Environment variables

```bash
cp .env.example .env
```

Edit `.env` with your real values:
```
MONGO_URI=mongodb://localhost:27017
DB_NAME=authdb
SECRET_KEY=your-secret-key-here
```

### Start background services

```bash
brew services start mongodb-community
brew services start redis
brew services start zookeeper
brew services start kafka
```

### Running the app

You need **four processes running simultaneously**, each in its own terminal:

**Terminal 1 — API server**
```bash
uvicorn main:app --reload
```

**Terminal 2 — fake SMTP server** (prints OTP emails to terminal instead of sending real ones)
```bash
python -m aiosmtpd -n -l localhost:1025
```

**Terminal 3 — Celery worker** (processes background email tasks)
```bash
celery -A celery_app worker --loglevel=info
```

**Terminal 4 — Kafka consumer** (batch writes signups to MongoDB)
```bash
python kafka_consumer.py
```

Visit `http://127.0.0.1:8000/docs` for interactive API documentation.

## Architecture — signup flow

```
POST /auth/signup
    │
    ├── Bloom filter check (no DB hit for new emails)
    │
    ├── Hash password (bcrypt)
    │
    ├── Write to Redis immediately (write-through cache)
    │   └── Login works instantly, before DB write
    │
    ├── Publish to Kafka topic "user_signups"
    │   └── Consumer batches 100 messages → single insert_many() to MongoDB
    │
    ├── Add email to bloom filter
    │
    └── Queue OTP email via Celery → aiosmtpd (dev) / real SMTP (prod)
```

## What I learned building this

Each phase introduced one new backend concept:

1. **Password hashing** — bcrypt, never store plaintext
2. **Stateless auth** — JWT, protected routes via dependency injection
3. **Cache-first architecture** — Redis, fallback to source of truth
4. **Abuse prevention** — rate limiting per IP with slowapi
5. **Async background processing** — Celery task queues for OTP delivery
6. **Token refresh flows** — long-lived sessions without re-entering credentials
7. **Probabilistic data structures** — bloom filters, false positives vs false negatives
8. **Event-driven architecture** — Kafka decouples API from DB, enables batch writes and backpressure handling

## Known limitations / production gaps

- Uses `aiosmtpd` (fake local SMTP) instead of real email delivery
- Bloom filter is in-memory only — resets on server restart (production would persist to Redis)
- Kafka batch size set to 5 for testing (production would use 100+)
- `SECRET_KEY` stored in `.env` only — production needs a secrets manager
- No HTTPS/TLS (would sit behind a reverse proxy in production)
- MongoDB and Redis run locally — production would use managed instances
- Rate limiting is per-IP only, not per-account
- No Google OAuth2 yet (next phase)
