# RideShield Workflow Guide

This guide is the practical companion to the main [README](../README.md). The README explains the product and architecture. This file explains how to run it, what each role does, and how to exercise the system end to end.

## What RideShield Does

RideShield is a parametric income-protection system for gig delivery workers.

The operating loop is:

```text
Observe disruption signals -> detect incident -> verify worker coverage -> score risk -> decide -> pay or review
```

Important product rule:

- workers do not file claims manually
- the system generates claims when a real disruption is detected

## Current System Shape

### Mocked input layer

These files simulate external signals:

- [weather_mock.py](/c:/Users/satvi/Desktop/RideShield_work/simulations/weather_mock.py)
- [aqi_mock.py](/c:/Users/satvi/Desktop/RideShield_work/simulations/aqi_mock.py)
- [traffic_mock.py](/c:/Users/satvi/Desktop/RideShield_work/simulations/traffic_mock.py)
- [platform_mock.py](/c:/Users/satvi/Desktop/RideShield_work/simulations/platform_mock.py)

### Real engine layer

These are the actual product core:

- [trigger_engine.py](/c:/Users/satvi/Desktop/RideShield_work/backend/core/trigger_engine.py)
- [claim_processor.py](/c:/Users/satvi/Desktop/RideShield_work/backend/core/claim_processor.py)
- [fraud_detector.py](/c:/Users/satvi/Desktop/RideShield_work/backend/core/fraud_detector.py)
- [decision_engine.py](/c:/Users/satvi/Desktop/RideShield_work/backend/core/decision_engine.py)
- [income_verifier.py](/c:/Users/satvi/Desktop/RideShield_work/backend/core/income_verifier.py)
- [payout_executor.py](/c:/Users/satvi/Desktop/RideShield_work/backend/core/payout_executor.py)

### Orchestration layer

- automatic monitoring: [trigger_scheduler.py](/c:/Users/satvi/Desktop/RideShield_work/backend/core/trigger_scheduler.py)
- manual demo control: [triggers.py](/c:/Users/satvi/Desktop/RideShield_work/backend/api/triggers.py)

### Frontend surfaces

- worker and onboarding flow
- admin operations
- demo runner

## Local Setup

### 1. Start the full stack

From the repo root:

```powershell
.\scripts\run_all.ps1
```

This starts:

- Docker Postgres
- FastAPI backend
- React frontend

### 2. Seed demo data

```powershell
.\venv\Scripts\python.exe -m scripts.seed_data
```

Seeded demo workers:

- Rahul: `+919876543210`
- Vikram: `+919876543211`
- Arun: `+919876543212`
- Priya: `+919876543213`
- Aman: `+919876543214`
- Farhan: `+919876543215`
- Sneha: `+919876543216`
- Neha: `+919876543217`
- Rohit: `+919876543218`

### 3. Open the app

- frontend: `http://localhost:3000`
- backend docs: `http://localhost:8000/docs`

## Auth And Roles

### Worker sign-in

- go to `/auth`
- enter worker phone number
- session is restored on refresh

### Admin sign-in

- go to `/auth`
- switch to admin sign-in
- credentials:
  - username: `admin`
  - password: `rideshield-admin`

## Worker Workflow

### A. New worker path

1. Open `/onboarding`
2. Register worker profile
3. View risk score and recommended plans
4. Inspect premium formula panel
5. Buy a weekly policy
6. Open worker dashboard

### B. Returning worker path

1. Open `/auth`
2. Sign in with phone
3. Go to dashboard
4. Review:
   - active policy
   - grouped incidents
   - claim status and reasoning
   - payout history
   - nearby disruptions

## Admin Workflow

1. Sign in as admin
2. Open `/admin`
3. Review:
   - claims in window
   - fraud rate
   - payout totals
   - loss ratio
   - worker activity index
   - live and recent disruptions
   - duplicate and extension audit log
   - next-week forecast
   - scheduler status
4. Resolve delayed claims from the review queue

## Demo Runner Workflow

1. Sign in as admin
2. Open `/demo`
3. Create a demo worker if needed
4. Run a scenario
5. Watch the frontend explain:
   - which signals crossed threshold
   - whether an incident was created or extended
   - how many claims were processed
   - how many were approved, delayed, or rejected
6. Open worker dashboard or admin panel to inspect downstream results
7. Reset simulators when done

## How Triggering Works Right Now

The external world is mocked, but the trigger logic is real.

Flow:

1. Scheduler or manual demo call starts a trigger cycle
2. Trigger engine fetches data from the simulator layer
3. Thresholds are evaluated
4. Matching signals are merged into one incident event for the zone and time window
5. Covered workers are identified
6. One claim per worker per incident is created
7. Fraud and decision logic run
8. Approved claims pay out, delayed claims go to admin review

## Geography And Locations

RideShield is no longer only driven by hardcoded frontend geography constants.

Current location model:
- cities and zones are bootstrapped into the database
- thresholds and baseline risk profiles are attached to zones
- onboarding, demo runner, and admin filters fetch location data from `/api/locations/*`
- scheduler reads active cities/zones from the DB first

Current supported cities:
- Delhi
- Mumbai
- Bengaluru
- Chennai

Current important rule:
- `zone_id` is the backend source of truth
- city/zone strings remain for compatibility and display

Current practical consequence:
- adding a supported zone within the current model is now a data/bootstrap concern, not only a frontend constant edit

## Current Product Guarantees

- claims are system-generated, not manually filed
- incident-based same-window claims do not stack into repeated payouts for the same worker
- duplicate and extension behavior is audited
- tests are isolated from the live dev database
- seed data can be rerun safely
- scheduler state is visible in health/admin surfaces
- location data is API-driven in the main user/admin flows

## Useful Docs

- [README.md](../README.md)
- [architecture.md](/c:/Users/satvi/Desktop/RideShield_work/docs/architecture.md)
- [api_reference.md](/c:/Users/satvi/Desktop/RideShield_work/docs/api_reference.md)
- [manual_review_script.md](/c:/Users/satvi/Desktop/RideShield_work/docs/manual_review_script.md)
- [DevNotes.md](/c:/Users/satvi/Desktop/RideShield_work/docs/DevNotes.md)
