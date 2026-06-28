# Auth System

A production-style authentication system built with FastAPI, as a learn-by-doing project covering JWT auth, Redis caching, rate limiting, OTP email verification via Celery, and refresh tokens.

## Features

- **Signup/Login** — passwords hashed with bcrypt, never stored in plain text
- **JWT authentication** — stateless access tokens, protected routes via FastAPI dependency injection
- **Redis caching** — cache-first login flow, falls back to MongoDB on cache miss
- **Rate limiting** — brute-force protection on login (5 requests/minute per IP)
- **OTP email verification** — signup triggers a background Celery task that emails a 6-digit code, expiring in 5 minutes
- **Refresh tokens** — long-lived (7-day) tokens that exchange for new short-lived access tokens without re-entering credentials

## Tech Stack

- **FastAPI** — web framework
- **MongoDB** (via Motor) — persistent user storage
- **Redis** — caching, OTP storage, refresh token storage, rate limiting, and Celery broker
- **Celery** — background task processing (OTP emails)
- **bcrypt** — password hashing
- **python-jose** — JWT creation and verification
- **slowapi** — rate limiting

## Project Structure

## Setup

### Prerequisites

- Python 3.11+
- MongoDB running locally (`brew install mongodb-community`)
- Redis running locally (`brew install redis`)

### Installation

```bash
git clone <your-repo-url>
cd auth-system
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Environment variables

Copy `.env.example` to `.env` and fill in real values:

```bash
cp .env.example .env
```

### Running the app

You'll need **three processes running simultaneously**, each in its own terminal:

**1. The API server**
```bash
uvicorn main:app --reload
```

**2. A local SMTP server** (for testing OTP emails — prints emails to the terminal instead of sending real ones)
```bash
python -m aiosmtpd -n -l localhost:1025
```

**3. The Celery worker** (processes background email tasks)
```bash
celery -A celery_app worker --loglevel=info
```

Once running, visit `http://127.0.0.1:8000/docs` for interactive API documentation.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|--------------|
| POST | `/auth/signup` | Register a new user, sends OTP email |
| POST | `/auth/login` | Authenticate, returns access + refresh tokens |
| POST | `/auth/verify-otp` | Verify email using the OTP code |
| POST | `/auth/refresh` | Exchange a refresh token for a new access token |
| GET | `/auth/me` | Get the current authenticated user (requires Bearer token) |

## What I learned building this

This project was built incrementally, phase by phase, to deeply understand each authentication concept rather than copy-pasting a finished solution. Each phase introduced one new idea:

1. Password hashing and basic CRUD
2. Stateless authentication with JWT
3. Cache-first architecture with Redis
4. Abuse prevention with rate limiting
5. Asynchronous background processing with Celery
6. Token refresh flows for long-lived sessions

## Known limitations / production gaps

- Uses a local fake SMTP server (`aiosmtpd`) instead of real email delivery
- `SECRET_KEY` and other secrets are stored in `.env` only — would need a proper secrets manager in production
- No HTTPS/TLS termination configured (would sit behind a reverse proxy in production)
- MongoDB and Redis run locally — production would use managed/hosted instances
- Rate limiting is per-IP only, not per-account