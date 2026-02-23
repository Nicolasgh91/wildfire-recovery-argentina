┌─────────────────────────────────────────────────────────────────────────────┐
│                    MODELO DE DATOS COMPLETO                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  payment_requests                      payment_webhook_logs                 │
│  ═════════════════                     ════════════════════                 │
│  id (uuid, pk)                         id (uuid, pk)                        │
│  user_id (uuid, fk)                    payment_request_id (uuid, fk)        │
│  status (enum)                         received_at (timestamptz)            │
│  provider (varchar)                    topic (varchar)                      │
│  purpose (varchar)                     action (varchar)                     │
│  amount_usd (numeric)                  raw_payload (jsonb)                  │
│  amount_ars (numeric)                  processing_result (varchar)          │
│  external_reference (unique)           error_message (text, nullable)       │
│  provider_payment_id (varchar)                                              │
│  provider_preference_id (varchar)      user_credits                         │
│  checkout_url (text)                   ════════════                         │
│  target_entity_type (varchar)          id (uuid, pk)                        │
│  target_entity_id (uuid, nullable)     user_id (uuid, fk)                   │
│  expires_at (timestamptz)              balance (integer)                    │
│  created_at (timestamptz)              updated_at (timestamptz)             │
│  updated_at (timestamptz)                                                   │
│  approved_at (timestamptz, nullable)   credit_transactions                  │
│  webhook_received_at (timestamptz)     ════════════════════                 │
│  retry_count (integer, default 0)      id (uuid, pk)                        │
│  metadata (jsonb)                      user_id (uuid, fk)                   │
│                                        amount (integer)                     │
│                                        type ('purchase'|'grant'|'spend')    │
│                                        payment_request_id (uuid, nullable)  │
│                                        description (text)                   │
│                                        created_at (timestamptz)             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘