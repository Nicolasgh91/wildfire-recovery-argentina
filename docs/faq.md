# ❓ Frequently Asked Questions (FAQs) – ForestGuard

This document answers common questions about ForestGuard and addresses common myths regarding the use of satellite data, wildfires, and environmental evidence.

---

## 📌 Frequently asked questions

### 1. Where do the fire data come from?

ForestGuard uses official open data from **NASA FIRMS** (**VIIRS and MODIS** sensors) and **Sentinel-2** (ESA / Copernicus). These sources are international standards used by governments, universities, and environmental agencies.

---

### 2. How reliable are the data?

The data are not only reliable but **auditable and reproducible**. ForestGuard adds normalization, traceability, and spatial context, reducing interpretation errors and false positives.

---

### 3. Does ForestGuard detect fires in real-time?

It supports **near real-time incremental ingestion**, subject to satellite feed availability. Additionally, it maintains a **complete history since 2015**, ideal for retrospective analysis and audits.

---

### 4. What is the difference between a detection and a fire?

A detection is a point thermal anomaly. ForestGuard groups multiple detections close in time and space to identify **actual fire events**.

---

### 5. Does ForestGuard store satellite images?

No. Sentinel-2 images are processed **on-demand** to generate reports and are then discarded. Only **metadata and final documents** are preserved, avoiding infrastructure overload.

---

### 6. What are environmental certificates?

They are **verifiable PDF documents**, with a cryptographic hash and QR code, allowing public validation of the authenticity and content of the generated report.

---

### 7. Can it detect construction after a fire?

Yes. ForestGuard analyzes time series of Sentinel-2 images to detect **land use changes**, such as buildings, roads, or pools, even years after the fire.

---

### 8. In which regions does ForestGuard work?

Currently, the focus is **Argentina**, but the architecture allows easy scaling to other countries with equivalent satellite data.

---

### 9. Does ForestGuard replace early warning systems?

No. ForestGuard complements those systems by providing **historical analysis, audit, and evidence**, without replacing brigades or operational alerts.

---

### 10. Who can use ForestGuard?

It is designed for public agencies, NGOs, companies, researchers, journalists, and citizens interested in environmental auditing.

---

## ⚖️ Myths vs. reality

### ❌ Myth: "Satellite data do not serve as evidence"

**✅ Reality:** They are used globally by state agencies and international bodies. ForestGuard converts them into reproducible technical evidence through traceability and verification.

---

### ❌ Myth: "A satellite point does not prove a fire"

**✅ Reality:** Correct. That is why ForestGuard does not work with isolated points, but with **consolidated events** derived from multiple detections.

---

### ❌ Myth: "Small fires don't matter"

**✅ Reality:** Low-surface fires in sensitive areas can be early indicators of environmental degradation or land misuse.

---

### ❌ Myth: "Satellite images are inaccurate"

**✅ Reality:** Sentinel-2 offers 10 m resolution, sufficient to detect clearings, constructions, and significant changes in the territory.

---

### ❌ Myth: "ForestGuard replaces brigades or alerts"

**✅ Reality:** It does not replace them; it adds value downstream with analysis, audit, and verifiable documentation.

---

### ❌ Myth: "It is necessary to store all images"

**✅ Reality:** No. ForestGuard processes images on demand and preserves only essential information.

---

### ❌ Myth: "PDF certificates are only informative"

**✅ Reality:** They are designed for administrative, legal, and compliance use, with verification hash and QR code.

---

### ❌ Myth: "ForestGuard is an experimental project"

**✅ Reality:** It has an operational pipeline, complete historical base, and architecture ready for production.

---

## 📍 Final note

ForestGuard seeks to transform open data into **responsible decisions and reliable environmental evidence**, facilitating transparency and long-term control.
