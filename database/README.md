# Database Migrations

Since the project uses Supabase, migrations should be applied via the Supabase SQL Editor.

## 🛠️ Required Actions (v3.2 - Security & Performance)

### 1. Full Database Schema (v3.2)
**File**: `schema.sql`

**Purpose**:
- Contains the **entire** database schema (Tables, Indexes, RLS Policies).
- Use this file to restore the database to a clean state or verify structure.
- Includes `citizen_reports`, `audit_events`, `fire_events` optimization, and security policies.

## 🔎 Verification

After applying `schema.sql`:
1.  Check that all tables exist (`citizen_reports`, `audit_events`, etc.).
2.  Check for indexes on `fire_events` (`idx_fire_events_start_date_desc`).
3.  Verify RLS is enabled on key tables in Supabase Dashboard.
