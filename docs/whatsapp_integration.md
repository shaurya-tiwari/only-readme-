# 📱 WhatsApp Integration — Technical Guide

This document explains how the RideShield WhatsApp integration works, its technical architecture, and its current deployment limitations.

---

## 🚀 Overview

The WhatsApp integration provides a low-friction conversational interface for gig workers to:
- **Onboard** (Select language, city, platform, and plan).
- **Check Status** (View current policy active status and risk levels).
- **Receive Proactive Alerts** (Get notified when a disruption like heavy rain is forecast in their zone).

---

## 🛠️ Technical Stack

- **API**: [Meta WhatsApp Cloud API](https://developers.facebook.com/docs/whatsapp/cloud-api) (v19.0).
- **Backend**: FastAPI (Python) hosting the conversational state machine.
- **Tunneling**: `ngrok` (for local development/testing).
- **Storage**: PostgreSQL (for session persistence and user settings).

---

## 🔄 Conversational Flow

The integration uses a **Stateful Webhook** approach:

1.  **Incoming Message**: Meta sends a POST request to `/api/whatsapp/webhook`.
2.  **State Management**: The `whatsapp_flow` manager retrieves the current `FlowState` for the sender's phone number.
3.  **Action Dispatch**:
    -   If it's a **Greeting** (e.g., "hi", "hello"), the system resets to the Language Selection state.
    -   If it's a **Button Reply**, the system processes the user's choice (e.g., city, plan) and advances to the next state.
4.  **Outgoing Message**: The `WhatsAppMetaProvider` sends instructions back to Meta using the configured `META_ACCESS_TOKEN`.

### Available States:
- `LANG_SELECTION`: Choosing between English and Hindi.
- `MAIN_MENU`: Home screen with "Start Protection" and "Check Status".
- `ONBOARD_NAME`, `ONBOARD_CITY`, `ONBOARD_PLATFORM`: Step-by-step registration.
- `ONBOARD_PLAN`: Plan selection (Smart Protect, Pro Max, etc.).
- `ONBOARD_PAYMENT`: Simulation of payment success.

---

## ⚠️ Important Limitations

> [!WARNING]
> **Test Number Restriction**
> Currently, the integration is configured to run on **Meta Test Numbers**. It will only work with phone numbers that have been manually added to the "Recipient list" in the Meta Developer Dashboard.

> [!IMPORTANT]
> **Production Readiness**
> To run on a live, public-facing WhatsApp business number, the following steps are required:
> 1.  **Meta Business Verification**: Your business must be verified by Meta.
> 2.  **App Review**: The RideShield app must pass Meta's official App Review.
> 3.  **Permanent Token**: Transition from a 24-hour temporary token to a System User Permanent Access Token.

---

## 🔗 Setup Instructions (Local)

1.  **Start Backend**: Ensure the FastAPI server is running on port `8000`.
2.  **Start Tunnel**: Run `ngrok http 8000`.
3.  **Update Meta**: Copy the ngrok URL into the **Webhook Configuration** in the Meta Developer Portal.
4.  **Verify**: Ensure the `VERIFY_TOKEN` matches the one in your `.env` file.

---

*Last updated: April 2026*
