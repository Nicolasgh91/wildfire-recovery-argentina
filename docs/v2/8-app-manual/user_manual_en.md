# ForestGuard - User Manual

**Version**: 2.0  
**Last Updated**: February 2026  
**Language**: English  
**Audience**: General users, researchers, professionals

---

## 📑 Table of Contents

1. [Introduction](#1-introduction)
2. [Getting Started](#2-getting-started)
3. [General Navigation](#3-general-navigation)
4. [Main Features](#4-main-features)
5. [Frequently Asked Questions](#5-frequently-asked-questions)
6. [Troubleshooting](#6-troubleshooting)
7. [Contact and Support](#7-contact-and-support)

---

## 1. Introduction

### 1.1 What is ForestGuard?

**ForestGuard** is a wildfire monitoring and analysis platform for Argentina that combines:

- 🛰️ **Satellite imagery** from Google Earth Engine (Sentinel-2)
- 🔥 **Fire detections** from NASA FIRMS (VIIRS/MODIS)
- 🌡️ **Climate data** from Open-Meteo
- 📊 **Spatial analysis** with PostGIS and H3 spatial indexing
- ⚖️ **Legal validation** according to Argentine Law 26.815

### 1.2 Who is ForestGuard for?

ForestGuard is designed for:

| Profile | Use Case |
|---------|----------|
| **Citizens** | Verify if land had fires before purchasing/renting |
| **Journalists** | Investigate fire patterns in specific areas |
| **NGOs** | Analyze recurrence trends in protected areas |
| **Legal experts** | Generate reports with satellite evidence for legal cases |
| **Researchers** | Study fire impact on native forests |
| **Prosecutors** | Obtain technical evidence for investigations |

### 1.3 What can I do with ForestGuard?

✅ **Query fire history** with advanced filters  
✅ **Verify land parcels** for legal prohibitions under Law 26.815  
✅ **Explore satellite images** before/during/after fires  
✅ **Generate PDF reports** with verifiable technical evidence  
✅ **Analyze recurrence** in areas of interest  
✅ **View public statistics** without registration

---

## 2. Getting Started

### 2.1 System Requirements

| Requirement | Specification |
|-------------|---------------|
| **Browser** | Chrome 90+, Firefox 88+, Safari 14+, Edge 90+ |
| **Connection** | Recommended: 5 Mbps or higher |
| **Device** | Desktop, tablet, or mobile (responsive design) |
| **JavaScript** | Enabled (required) |

### 2.2 Account Registration

#### Step 1: Access the Landing Page

1. Go to **https://forestguard.freedynamicdns.org/**
2. You'll see the welcome screen with the **"ForestGuard"** title
3. Subtitle: *"Satellite evidence to understand what happened to the territory after a fire"*

#### Step 2: Create Account

**Option A: Email Registration**

1. Click **"Create account"** (below the login form)
2. Fill out the form:
   - **Full name** (e.g., John Doe)
   - **Email** (e.g., john.doe@example.com)
   - **Password** (minimum 8 characters, include uppercase, numbers, and symbols)
   - **Confirm password**
3. Accept **Terms and Conditions** (required checkbox)
4. Click **"Sign up"**
5. Verify your email and click the confirmation link

**Option B: Google Registration**

1. Click **"Continue with Google"** button
2. Select your Google account
3. Authorize ForestGuard access
4. You'll be automatically redirected to the dashboard

> **💡 Tip**: Google registration is faster and doesn't require email verification.

### 2.3 Login

1. Enter your **email** and **password**
2. (Optional) Check **"Remember me"** to keep session active
3. Click **"Sign in"**

**Forgot your password?**
1. Click **"Forgot password?"**
2. Enter your registered email
3. You'll receive a recovery link via email
4. Create a new password

---

## 3. General Navigation

### 3.1 Navigation Bar

The top bar contains:

```
┌────────────────────────────────────────────────────────────────┐
│  🌳 ForestGuard  │  Home  │  Map  │  History  │  [User]        │
└────────────────────────────────────────────────────────────────┘
```

| Element | Description |
|---------|-------------|
| **ForestGuard Logo** | Click to return home |
| **Home** | Main dashboard with statistics |
| **Map** | Geographic visualization of fires |
| **History** | Filterable query of past fires |
| **[User Name]** | Dropdown menu with account options |

### 3.2 User Menu

Clicking your name (top right corner) gives you access to:

- **My profile** - View and edit personal information
- **Verify land** - Legal land use audit
- **Satellite exploration** - Generate reports with images
- **Certificates** - Visual evidence download center
- **Settings** - Account preferences
- **Logout** - Close session

### 3.3 Language

Currently available in **Spanish (Argentina)**.

> **🚧 In development**: English version (upcoming release)

---

## 4. Main Features

### 4.1 Dashboard (Home)

#### What is it?
Overview with statistics and quick access to key features.

#### What will you see?

**Main KPIs:**
- **Total fires** from last year
- **Affected hectares** (cumulative)
- **Active fires** (real-time)
- **Average duration** (in days)

**Charts:**
- **Time series**: Fires per month (last 12 months)
- **Distribution by province**: Top 5 most affected provinces
- **Fire status**: Active vs. Extinguished

**Quick Access:**
- 📍 **Verify land** → Featured button
- 🛰️ **Explore images** → Access to satellite exploration
- 📊 **View map** → Geographic visualization

#### How to use it?

1. **View general statistics**: KPIs update automatically
2. **Filter by date**: Use date range selector (top corner)
3. **Click "See more"** for details of each chart

---

### 4.2 Fire Map

#### What is it?
Interactive geographic visualization of all detected fires in Argentina.

#### Map Layers

| Layer | Description | Toggle |
|-------|-------------|--------|
| **Active fires** | Pulsating red markers | ✅ Default |
| **Extinguished fires** | Gray markers | ⬜ Optional |
| **Protected areas** | Green polygons | ⬜ Optional |
| **Heat map** | Fire density | ⬜ Optional |

#### Controls

```
┌───────────────────────────────────────────┐
│  [Search location...]                     │
│  ┌──────────────────────────────────────┐ │
│  │                                      │ │
│  │       🗺️ INTERACTIVE MAP            │ │
│  │                                      │ │
│  └──────────────────────────────────────┘ │
│  [− Zoom +]  [🏠 Center]  [🔍 Filters]   │
└───────────────────────────────────────────┘
```

**Available controls:**
- **Zoom**: Mouse wheel or +/- buttons
- **Pan**: Click and drag to move the map
- **Search**: Enter a province, city, or address
- **Filters**: Date range, province, status

#### How to use it?

**View fire details:**
1. Click on a map marker
2. A popup will open with:
   - Fire name
   - Start date
   - Current status
   - Affected hectares
   - Maximum FRP (Fire Radiative Power)
3. Click **"View details"** for complete info

**Filter fires:**
1. Click the **"Filters"** button (top right corner)
2. Select criteria:
   - **Date range** (e.g., last 30 days)
   - **Province** (e.g., Córdoba)
   - **Status** (active, extinguished, contained)
3. Click **"Apply"**
4. The map will update automatically

**Activate layers:**
1. Click the layers icon (🗂️)
2. Check/uncheck desired layers
3. Changes apply in real-time

---

### 4.3 Fire History

#### What is it?
Filterable table with all recorded fires, with search, sorting, and export options.

#### Table Columns

| Column | Description |
|--------|-------------|
| **Name** | Fire identification (auto-generated) |
| **Province** | Geographic location |
| **Start date** | First satellite detection |
| **End date** | Last detection or confirmed extinction |
| **Status** | Active / Extinguished / Contained |
| **Area (ha)** | Estimated affected hectares |
| **Max FRP** | Maximum Fire Radiative Power (MW) |
| **Actions** | Buttons: View details, Download report |

#### Available Filters

**Text search:**
- Enter province name, locality, or fire ID
- Real-time search (updates as you type)

**Advanced filters:**
1. **Date range**: Calendar with start and end
2. **Province**: Dropdown with all provinces
3. **Status**: Multi-select (active, extinguished, contained)
4. **Minimum area**: Only fires > X hectares
5. **In protected area**: Checkbox to filter only protected areas

#### How to use it?

**Search for a specific fire:**
1. Use the search bar (🔍 icon)
2. Enter: province, approximate date, or ID
3. The table filters automatically

**Sort results:**
1. Click on any column header
2. First time: ascending order (↑)
3. Second time: descending order (↓)
4. Third time: returns to original order

**Export data:**
1. Apply desired filters
2. Click **"Export"** (top right corner)
3. Select format:
   - **CSV** (Excel, Google Sheets)
   - **JSON** (programming, APIs)
4. Maximum: 10,000 records per export

**Pagination:**
- Results per page: 20 (default), 50, 100
- Navigation: ◀ Previous | 1 2 3 ... | Next ▶

---

### 4.4 Verify Land (Legal Audit)

#### What is it?
Tool to investigate whether a land parcel had fires and determine legal prohibitions under **Law 26.815**.

> **⚖️ Legal Framework**: Law 26.815 prohibits land use changes for **60 years** in native forests and **30 years** in agricultural zones after a fire.

#### Usage Flow

**Step 1: Search for Location**

Three ways to search:
1. **By address**: E.g., "Av. Córdoba 1200, CABA"
2. **By locality**: E.g., "Villa Carlos Paz, Córdoba"
3. **By national park**: E.g., "Quebrada del Condorito National Park"
4. **Mark on map**: Direct click on interactive map

**Step 2: Define Analysis Area**

Select search radius with predefined chips:

| Option | Radius | Recommended use |
|--------|--------|-----------------|
| **Surroundings** | 500 m | Small parcel, urban lot |
| **Zone** | 1 km | Medium field, rural area |
| **Wide** | 3 km | Large field, regional analysis |
| **Custom** | Manual | Advanced (in "Advanced Options") |

**Step 3: Advanced Options (optional)**

Click **"Advanced Options"** to:
- Adjust exact coordinates (decimal lat/lon)
- Enter cadastral ID (if known)
- Custom radius (up to 5000 m)

**Step 4: Verify**

1. Click **"Verify"** (main green button)
2. Verification checklist is shown:
   - ✅ Were there fires in recent years in this zone?
   - ✅ Did vegetation recover or remain degraded?
   - ✅ Do fire signs persist in the area?
   - ✅ What do public sources and local records say?
3. Loading states: "Searching fires..." → "Analyzing protected area..." → Results

#### Results

**If NO fires:**
```
✅ No fires found in the analyzed area
   Radius: 1 km from lat -31.42, lon -64.18
   Period analyzed: last 10 years
```

**If there ARE fires:**

```
⚠️ 2 fires found in the area

┌──────────────────────────────────────────────────────────────┐
│ Fire 1: Sierras Chicas                                       │
│ • Date: March 15, 2024                                       │
│ • Distance: 450 m from query point                           │
│ • Protected area: Quebrada del Condorito National Park       │
│ • Prohibition until: March 15, 2084 (60 years)               │
│ • Visual evidence: [View satellite thumbnail]                │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ Fire 2: Los Gigantes                                         │
│ • Date: January 8, 2023                                      │
│ • Distance: 1.2 km                                           │
│ • Category: Agricultural zone                                │
│ • Prohibition until: January 8, 2053 (30 years)              │
└──────────────────────────────────────────────────────────────┘
```

**Download Report:**
- Click **"Download PDF report"**
- PDF includes:
  - SHA-256 hash for verification
  - Map with land location and fire perimeters
  - Satellite images (thumbnails)
  - Data sources used
  - Legal disclaimer

#### Interpreting Results

> **⚠️ Important**: This tool provides technical evidence for investigation. It does **NOT constitute legal advice**. Consult with a specialized attorney for legal or contractual decisions.

**Guided microcopy:**
- *"Some fires are accidental; others may have interests behind them. Here you can look at evidence and draw your own conclusions."*
- *"This does not prove intentionality by itself. It serves to contrast narratives with observable evidence."*

---

### 4.5 Satellite Exploration

#### What is it?
6-step wizard to observe, compare, and understand changes in fire-affected terrain using HD satellite images.

> **💰 Cost**: Each HD image requested costs **USD 0.50** (1 credit). Cost transparency is shown **before** processing.

#### Report Types

| Type | Description | Audience | Max Images |
|------|-------------|----------|------------|
| **Historical** | Post-fire recovery analysis | General | 12 |
| **Judicial** | Technical evidence for legal cases | Legal experts, prosecutors | Unlimited |

#### Wizard Flow

**Step 1: Fire Search**

1. Use **autocomplete** to search by:
   - Province (e.g., "Córdoba")
   - Date range (e.g., "January 2024")
   - Fire name
2. Select fire from list

**Step 2: Report Configuration**

Define parameters:

| Parameter | Options | Description |
|-----------|---------|-------------|
| **Type** | Historical / Judicial | According to your need |
| **Time range** | Before and after fire | Date selector |
| **# of images** | 1 - 12 (historical) | Frequency: weekly, biweekly, monthly |
| **Visualizations** | NDVI, NBR, SWIR, RGB | Multi-select |

**Available visualizations:**
- **RGB**: Natural color (like a photo)
- **SWIR**: Short-Wave Infrared (highlights active fires)
- **NDVI**: Normalized Difference Vegetation Index (vegetation health)
- **NBR**: Normalized Burn Ratio (fire severity)

**Step 3: Preview and Costing**

System shows:

```
┌──────────────────────────────────────────────────────────────┐
│ YOUR EXPLORATION SUMMARY                                     │
│                                                              │
│ Fire: Sierras Chicas                                         │
│ Period: March 1 - June 1, 2024                              │
│                                                              │
│ 📸 Images to generate: 12                                    │
│ 🎨 Visualizations: NDVI, NBR, RGB (× 3 per date)            │
│ 💰 Total cost: USD 6.00 (12 credits)                        │
│ ⏱️ Estimated time: 90 seconds                                │
│                                                              │
│ [◀ Back] [Confirm and Pay ✓]                                │
└──────────────────────────────────────────────────────────────┘
```

**Step 4: Confirmation and Payment**

1. Review summary
2. Click **"Confirm and Pay"**
3. You'll be redirected to **MercadoPago**
4. Complete payment (card, MercadoPago account, cash)
5. You're automatically returned to ForestGuard

**Step 5: Generation (Polling)**

Real-time visible status:

```
🔄 Generating your report...

✅ Searching satellite images        [████████] 100%
🔄 Processing visualizations         [███░░░░░]  40%
⏳ Generating PDF                    [░░░░░░░░]   0%

Progress: 47% completed
Estimated time remaining: 53 seconds
```

**Step 6: Download**

Once completed:

```
✅ Your exploration is ready!

📄 Report: sierras_chicas_2024.pdf (12.4 MB)
🔐 SHA-256 Hash: abc123def456...
📅 Generated: February 9, 2026, 18:45 UTC
⏰ Available for: 90 days

[Download PDF ⬇]  [Verify Hash 🔍]  [New Exploration +]
```

#### PDF Content

The report includes:

1. **Cover** with ForestGuard logo + watermark
2. **Executive summary**: Fire data, affected area, severity
3. **Timeline**: Key event chronology
4. **Visual comparisons**:
   - Before/After with slider
   - NDVI time series (chart)
   - Severity map (dNBR)
5. **Selected HD images** (12 pages)
6. **Technical metadata**:
   - Data sources (NASA FIRMS, Sentinel-2, Open-Meteo)
   - GEE system index (reproducibility)
   - Cloud coverage per image
7. **Disclaimers and limitations**
8. **QR code** for public verification
9. **SHA-256 hash** of complete document

#### Hash Verification

To verify authenticity:

1. Copy hash from PDF
2. Go to **https://forestguard.freedynamicdns.org/verify/[hash]**
3. Or scan QR code from PDF
4. You'll see confirmation: ✅ "Valid document, generated on [date]"

---

### 4.6 Certificates (Visual Exploration Center)

#### What is it?
Satellite evidence download center with up to **12 full HD images** selectable for research and awareness.

> **🎯 Focus**: Curiosity and educational investigation (not legal certificates with digital signature)

#### Difference with Satellite Exploration

| Aspect | Certificates | Satellite Exploration |
|--------|--------------|------------------------|
| **Focus** | Educational, visual | Technical, professional |
| **Image limit** | 12 maximum | 12 (historical) / unlimited (judicial) |
| **Output** | Customizable PDF | Technical PDF with complete metadata |
| **Cost** | TBD | USD 0.50/image |
| **Narrative** | "See with your own eyes" | "Verifiable evidence" |

#### 4-Step Flow

**Step 1: Area Selection**

1. Search location by address, locality, or park
2. Or mark directly on interactive map
3. Define analysis perimeter (polygon or radius)

**Step 2: Date/Image Selection**

```
┌──────────────────────────────────────────────────────────────┐
│ IMAGE TIMELINE                                               │
│                                                              │
│ Pre-fire       During      Post 3 months    Post 1 year     │
│     ●──────────── ● ─────────── ● ────────────── ●          │
│   📅 Mar 1     Mar 15      Jun 15         Mar 15 +1         │
│                                                              │
│ Selected images: 8 of 12                                    │
│                                                              │
│ [Clickable thumbnails with multi-select]                    │
│ [✓] Mar 1  [✓] Mar 15  [✓] Mar 20  [ ] Apr 1  [✓] Apr 15   │
└──────────────────────────────────────────────────────────────┘
```

**Timeline with predefined milestones:**
- **Pre-fire** (7-15 days before)
- **During** (detection date)
- **Post 3 months** (early recovery)
- **Post 1 year** (long-term recovery)

**Step 3: Preview and Summary**

**Before/After Comparator:**
```
┌────────────────────────────────────────────┐
│  BEFORE (Mar 1)     │  AFTER (Jun 15)      │
│                     │                      │
│  [Satellite image]  │  [Satellite image]   │
│   Dense vegetation  │  Burned area         │
│                     │                      │
│  ← Slide to compare →                      │
└────────────────────────────────────────────┘
```

**What your PDF includes:**
- ✅ 8 selected full HD images
- ✅ Temporal comparison (before/during/after)
- ✅ Indicators per image:
  - 🌿 Healthy vegetation (high NDVI)
  - 💧 Water stress (low NDVI)
  - 🔥 Fire scar (dNBR)
- ✅ Transparent sources (NASA, ESA, Google)
- ✅ Known limitations (cloudiness, resolution)

**Step 4: Generation and Download**

1. Click **"Generate my PDF"**
2. Document is assembled with what you chose
3. Download available in 60-90 seconds

#### Customizable PDF

The report tells a **visual story**:

1. **Intro**: "What happened in [area name]"
2. **Context**: Location, key dates, affected area
3. **Time journey**:
   - "Before the fire" (image + description)
   - "During the fire" (image + SWIR highlighting fire)
   - "3 months later" (image + NDVI showing recovery)
   - "1 year later" (image + final comparison)
4. **Translated indicators**:
   - 🌿 "Healthy vegetation" instead of "NDVI 0.8"
   - 💧 "Soil moisture" instead of "SM %"
   - 🔥 "Damage severity" instead of "dNBR class"
5. **Sources and limitations** in simple language

#### Learning Micro-moments

**Interface tooltips:**
- Hover over "NDVI" → "Measures how green and healthy vegetation is"
- Hover over "dNBR" → "Indicates how much damage the fire caused (from 1 to 10)"
- Hover over "Sentinel-2" → "European satellite that takes Earth photos every 5 days"

**Labels with human meaning:**
- ❌ "SWIR Band 12, 2190nm"
- ✅ "Infrared to see active fire"

---

### 4.7 My Profile

#### What can I do?

**Personal Information:**
- View and edit full name
- Change email (requires re-verification)
- Update password
- Change profile picture (optional)

**Credits (if applicable):**
- View current credit balance
- Consumption history
- Recharge credits (MercadoPago)

**Activity History:**
- Land audits performed
- Satellite explorations generated
- Certificates downloaded

**Security:**
- Enable two-factor authentication (2FA)
- View connected devices
- Close active sessions

---

## 5. Frequently Asked Questions

### 5.1 About the Data

**Where does the fire data come from?**

Data comes from multiple reliable sources:
- **NASA FIRMS**: Fire detections via VIIRS and MODIS satellites (375m and 1km resolution)
- **Sentinel-2**: High-resolution optical images (10-20m) from European Space Agency
- **Open-Meteo**: Climate data (temperature, humidity, wind)
- **Official data**: Protected areas of Argentina (National Parks Administration)

**How often is data updated?**

- **Fire detections**: Every 6-12 hours (depending on NASA FIRMS availability)
- **Satellite images**: New images every 5 days (Sentinel-2)
- **Public statistics**: Daily update at 02:00 UTC
- **Active fire carousel**: Daily generation at 01:00 UTC

**How accurate is the data?**

Each fire has a **Reliability Score** (0-100) based on:
- Satellite detection confidence (40%)
- Image quality (20%)
- Available climate data (20%)
- Independent detections (20%)

Classification:
- **High** (≥ 80): High confidence data
- **Medium** (50-79): Moderate confidence
- **Low** (< 50): Limited data, verify with additional sources

### 5.2 About Law 26.815

**What is Law 26.815?**

Argentine National Fire Management Law that establishes:
> *"Land use changes are prohibited for 60 years in areas of native forests or protected areas affected by fires. In agricultural zones and grasslands, the prohibition is 30 years."*

**Are prohibition dates official?**

ForestGuard calculates dates **automatically** based on:
1. Fire date (satellite detection)
2. Location (intersection with protected areas)
3. Legal category (native forest vs. agricultural zone)

> **⚠️ Important**: These dates are **indicative**. For official documentation, consult with the enforcement authority of your province.

**Can I use ForestGuard reports in legal procedures?**

Yes, our reports include:
- ✅ Verifiable SHA-256 hash
- ✅ Authentication QR code
- ✅ Transparent data sources
- ✅ Reproducible technical metadata

However, we **recommend** supplementing with:
- Official technical expertise
- Consultation with notary or specialized lawyer
- Verification with local enforcement authorities

### 5.3 About Costs and Payments

**Is ForestGuard free?**

**Free** features (without registration):
- View public statistics
- Explore fire map
- Query basic history

**Free** features (with registration):
- Complete dashboard with filters
- Verify land parcels (legal audit)
- Download basic reports (thumbnails)

**Paid** features:
- Satellite exploration with HD images: **USD 0.50 per image**
- Unlimited judicial reports: According to number of images

**How do I pay?**

We accept payments via **MercadoPago**:
- Credit/debit cards
- MercadoPago account
- Cash (Rapipago, Pago Fácil)

**Credit system:**
- 1 credit = USD 0.50
- 1 HD image = 1 credit
- You can buy packs: 10, 20, 50, 100 credits

**Are there refunds?**

Yes, you can request a refund up to **24 hours** after purchase if:
- You didn't download the generated PDF
- There was a technical error in generation

### 5.4 About Privacy and Security

**What data does ForestGuard collect?**

We collect:
- Email and name (registration)
- Search and query history
- Generated reports
- Land audit logs (legally required)

We do **NOT** collect:
- Real-time location
- Biometric data
- Sensitive information unrelated to the service

**Are my queries private?**

Yes. Only you and ForestGuard administrators can see your history.

**Exception**: `land_use_audits` (land verification) are recorded in immutable logs for **legal compliance** (Law 26.815), but without personally identifiable information.

**Can I delete my account?**

Yes, you can request account deletion from:
1. **My Profile** → **Settings** → **Delete account**
2. Confirm with password
3. Your personal data is deleted in **30 days**

> **Note**: Audit logs are maintained for legal requirements, but anonymized (without email or name).

---

## 6. Troubleshooting

### 6.1 Cannot Login

**Problem**: "Incorrect email or password"

**Solutions:**
1. Verify your email is spelled correctly
2. Check if you activated your account via email (check spam)
3. Use **"Forgot password?"** to recover access
4. If you registered with Google, use the **"Continue with Google"** button

**Problem**: "Account not verified"

**Solutions:**
1. Look for verification email in your inbox
2. Check **Spam** or **Promotions** folder
3. Click **"Resend verification email"** on login screen

### 6.2 Map Doesn't Load

**Problem**: Blank screen or map without markers

**Solutions:**
1. **Check your Internet connection**
2. **Disable script blockers** (AdBlock, uBlock)
3. **Refresh page** (F5 or Ctrl+R)
4. **Clear browser cache**:
   - Chrome: Ctrl+Shift+Del → "Cached images and files"
5. **Try in private/incognito browser**

### 6.3 CSV Export Fails

**Problem**: "Error exporting data" or empty file

**Solutions:**
1. **Reduce date range** (maximum 10,000 records)
2. **Apply more filters** to limit results
3. **Try exporting in JSON** instead of CSV
4. If it persists, **contact support** with:
   - Applied filters
   - Estimated number of records
   - Exact error message

### 6.4 Report Generation Takes Too Long

**Problem**: "Processing..." for more than 5 minutes

**Normal times:**
- Historical report (12 images): 60-120 seconds
- Judicial report (30+ images): 3-5 minutes

**If it exceeds time:**
1. **Don't close the tab** (process continues in background)
2. Wait up to 10 minutes (there may be GEE congestion)
3. If it shows "Error", check:
   - Your Internet connection didn't drop
   - You have sufficient credits
4. Contact support with `investigation_id` (appears in URL)

### 6.5 Verification Hash Doesn't Match

**Problem**: When verifying PDF hash, it says "Not valid"

**Possible causes:**
1. **PDF was modified** (edited, annotated, compressed)
2. **Hash copied incorrectly** (with spaces or extra characters)
3. **File corrupted** during download

**Solutions:**
1. **Re-download PDF** from your history in ForestGuard
2. **Don't edit PDF** before verifying hash
3. **Copy complete hash** (64 hexadecimal characters)
4. Use **QR code** from PDF for automatic verification

---

## 7. Contact and Support

### 7.1 Contact Form

**Access**: From site footer → **"Contact"**

**Form:**
- Full name
- Email
- Subject (dropdown with categories)
- Message (detailed description)
- Attachment (optional, max 5 MB: .jpg, .png, .pdf)

**Subject categories:**
- 💡 General inquiry
- 🐛 Report a bug
- 💳 Payment issue
- 🔒 Security and privacy
- 🌟 Improvement suggestion

**Response time:** 24-48 business hours

### 7.2 Technical Questions (GitHub)

For developers and advanced users:

**GitHub Issues**: https://github.com/[user]/forestguard/issues

Ideal for:
- Reporting bugs with technical logs
- Requesting new features
- Contributing code

### 7.3 Community and Social Media

- **Twitter/X**: @ForestGuardArg (updates, incidents)
- **LinkedIn**: ForestGuard (use cases, testimonials)
- **Email**: support@forestguard.app

---

## 📚 Glossary of Terms

| Term | Meaning |
|------|---------|
| **FRP** | Fire Radiative Power - Fire radiative power in megawatts (MW). Higher FRP = higher fire intensity. |
| **NDVI** | Normalized Difference Vegetation Index - Index measuring vegetation health (0 = no vegetation, 1 = dense healthy vegetation). |
| **NBR** | Normalized Burn Ratio - Ratio identifying burned areas and their severity. |
| **dNBR** | Difference NBR - NBR difference before and after fire to measure damage severity. |
| **SWIR** | Short-Wave Infrared - Infrared band allowing to see active fires and see through smoke. |
| **GEE** | Google Earth Engine - Google's geospatial analysis platform. |
| **Sentinel-2** | European Space Agency's Earth observation satellite (10-20m resolution). |
| **VIIRS/MODIS** | NASA satellite instruments for fire detection (375m and 1km resolution). |
| **PostGIS** | PostgreSQL extension for geospatial data. |
| **H3** | Uber's hexagonal spatial indexing system. |
| **RLS** | Row Level Security - Database row-level security. |
| **SHA-256 Hash** | 256-bit cryptographic signature verifying document integrity. |

---

**End of User Manual v2.0**

For more information, visit: **https://forestguard.freedynamicdns.org/**

*Last updated: February 2026*
