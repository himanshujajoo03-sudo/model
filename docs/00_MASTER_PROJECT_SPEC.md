# SIH26069 — National Weather Big Data Analytics Platform

## Master Project Specification

**Document:** `00_MASTER_PROJECT_SPEC.md`
**Version:** 1.0
**Status:** MASTER SOURCE OF TRUTH
**Hackathon Duration:** 5 Days
**MVP Geographic Scope:** Maharashtra — Mumbai, Nagpur, Nashik

---

# 1. Project Overview

## 1.1 Project Name

**National Weather Big Data Analytics Platform**

## 1.2 SIH Problem Statement

Design and develop a scalable National Weather Big Data Analytics Platform capable of collecting and processing real-time weather-related information for India from multiple internet-based sources including:

* Social media platforms
* Public datasets
* Websites
* APIs
* Citizen reports

The platform should automatically collect weather-related posts and information tagged with `#IMD` and other relevant weather hashtags, along with metadata such as:

* Date and time
* City
* State
* GPS location
* Photos
* Videos
* Event category

The platform should use big-data technologies and open-source tools for:

* Large-scale data ingestion
* Real-time processing
* Storage
* Analytics
* Visualization

Machine learning and AI techniques should assist with:

* Fake/misleading report detection
* Source verification
* Duplicate detection
* Weather-event classification

The platform must provide a web-based dashboard and Admin Panel supporting:

* Date-wise filtering
* Event-wise filtering
* Location-wise filtering
* Verification-status tracking
* Real-time visualization
* Analytics

---

# 2. Project Objective

The objective is to build a **lightweight, scalable, replicable and open-source weather intelligence pipeline** that converts fragmented weather information from multiple sources into structured, deduplicated, categorized, credibility-scored and geospatially visualized weather events.

The system is intended to improve:

* Situational awareness
* Information discovery
* Report verification
* Event identification
* Geographic understanding
* Historical analysis

The platform is **not a replacement for IMD weather forecasting systems**.

It is an **information aggregation, event intelligence, verification and visualization platform**.

---

# 3. Core Differentiator

## Lightweight, Replicable, Open Pipeline

The system should be designed so that it can eventually be deployed by:

* District offices
* Block offices
* NGOs
* Disaster-management organizations
* Local authorities

without requiring national-scale HPC infrastructure.

The architecture should use open-source and relatively lightweight components wherever practical.

---

# 4. MVP Scope

Because the hackathon duration is only five days, the MVP will focus on a limited geographic scope while keeping the architecture expandable.

## 4.1 Geographic Scope

### Architecture

The data model and APIs must remain capable of supporting:

> India → State → District → City → Coordinates

### MVP Demonstration

Only three Maharashtra locations will be used:

1. **Mumbai**
2. **Nagpur**
3. **Nashik**

These locations are selected to demonstrate contrasting weather-event scenarios.

### Mumbai

Primary scenarios:

* Heavy rainfall
* Urban flooding
* Waterlogging
* Thunderstorms

### Nagpur

Primary scenarios:

* Heatwave
* High temperature
* Thunderstorms
* Strong winds

### Nashik

Primary scenarios:

* Heavy rainfall
* Flooding
* Thunderstorms
* Hailstorms

The system must not hard-code the application architecture around these three locations.

Additional locations can be added through configuration/data.

---

# 5. Data Sources

The platform supports six operational source categories plus synthetic data for testing.

## 5.1 Social Media

Purpose:

Collect weather-related posts and reports associated with:

* `#IMD`
* `#Weather`
* `#HeavyRain`
* `#Flood`
* `#Thunderstorm`
* `#Heatwave`
* `#StrongWinds`
* `#Fog`
* `#DustStorm`

Implementation:

A dedicated **Social Media Source Adapter**.

Production architecture:

```text
Official Platform API
        ↓
Social Media Adapter
        ↓
Canonical Weather Event
```

Hackathon fallback:

```text
Controlled/Simulated Social Feed
        ↓
Same Social Media Adapter
        ↓
Canonical Weather Event
```

The system must not claim unrestricted scraping of platforms whose APIs/access policies do not permit it.

---

# 6. RSS Feeds

RSS is a first-class source type.

Purpose:

* Automatically collect weather-related news and updates
* Provide a structured alternative to direct website scraping
* Demonstrate continuous web-source ingestion

Pipeline:

```text
RSS Feed
   ↓
RSS Collector
   ↓
XML Parser
   ↓
Content Extraction
   ↓
Weather Event Extraction
   ↓
Canonical Event
```

RSS metadata may include:

* Title
* Description
* Publication time
* URL
* Author
* Category

Location can be extracted from the content and enriched when coordinates are unavailable.

---

# 7. Websites

A dedicated **Website Source Adapter** must be supported.

Purpose:

Collect weather-related information from selected publicly accessible websites that may not expose an RSS feed.

Pipeline:

```text
Website
   ↓
Fetcher
   ↓
HTML/Text Extraction
   ↓
Weather/Event NLP
   ↓
Location Extraction
   ↓
Canonical Weather Event
```

The MVP should use a controlled allowlist of suitable websites rather than attempting to crawl the entire internet.

---

# 8. Weather APIs

Weather APIs provide structured weather observations.

Example:

**Open-Meteo**

Potential fields:

* Temperature
* Precipitation
* Wind speed
* Humidity
* Weather conditions
* Observation timestamp
* Coordinates

API data can be used both as a source of weather observations and as supporting evidence for credibility scoring.

---

# 9. Public/Government Datasets

The platform must support ingestion of public or government weather-related datasets.

Supported formats may include:

* CSV
* JSON
* Parquet

Historical datasets can be loaded through batch ingestion rather than requiring real-time streaming.

---

# 10. Citizen Reports

The platform provides a web interface through which citizens can submit weather reports.

A citizen report may contain:

* Description
* Event category
* Timestamp
* City
* District
* State
* GPS coordinates
* Photo
* Video

Pipeline:

```text
Citizen
   ↓
React Form
   ↓
FastAPI
   ↓
Validation
   ↓
Canonical Event
   ↓
Kafka
```

---

# 11. Synthetic Data

Synthetic data is not considered a real external source.

It is used for:

* Load testing
* Pipeline testing
* Demonstrating scalability
* Generating 100K+ / 1M+ records
* Testing duplicate detection
* Testing credibility scoring
* Testing event classification

The generated data must be clearly identified as synthetic.

The project must never present synthetic records as genuine social-media or citizen reports.

---

# 12. Canonical Weather Event

All source adapters must convert their input into a common **Canonical Weather Event**.

The downstream pipeline must not need separate processing logic for every source.

Conceptual flow:

```text
Social Media ─┐
RSS ──────────┤
Website ──────┤
Weather API ──┤
Dataset ──────┤
Citizen ──────┤
Synthetic ────┘
       ↓
Source Adapters
       ↓
Canonical Weather Event
       ↓
Kafka
```

---

# 13. Required Event Metadata

A canonical event should support:

### Identity

* `event_id`
* Source ID

### Source

* `source_type`
* `source_name`
* `source_url`
* `source_trust_score`

### Time

* `timestamp`
* `ingestion_timestamp`

### Location

* Latitude
* Longitude
* City
* District
* State

### Event

* Category
* Severity
* Description

### Social metadata

* Hashtags
* Author/source identifier where appropriate

### Media

* Photos
* Videos

### AI

* Classification
* Classification confidence
* Duplicate score
* Credibility score

### Verification

* Verification status
* Verified by
* Verification timestamp

### Clustering

* Cluster ID

The final exact JSON schema will be defined in:

`02_DATA_SCHEMA.md`

---

# 14. Weather Event Taxonomy

Initial supported categories:

```text
rainfall
heavy_rainfall
flood
thunderstorm
lightning
heatwave
fog
dust_storm
strong_wind
hailstorm
cyclone
other
```

The taxonomy may be extended later, but new categories must not be added casually during the five-day MVP.

---

# 15. Big Data Architecture

The primary architecture is:

```text
                    DATA SOURCES
                         │
       ┌─────────┬───────┼───────┬─────────┐
       ↓         ↓       ↓       ↓         ↓
    Social    Websites  RSS     APIs    Datasets
       │         │       │       │         │
       └─────────┴───────┼───────┴─────────┘
                         │
                      Citizens
                         │
                         ↓
                  SOURCE ADAPTERS
                         ↓
                    NORMALIZATION
                         ↓
                       KAFKA
                         ↓
              SPARK STRUCTURED STREAMING
                         ↓
              ┌──────────┼──────────┐
              ↓          ↓          ↓
         Validation  Deduplication  Aggregation
              │          │          │
              └──────────┼──────────┘
                         ↓
                       AI/ML
                         ↓
          ┌──────────────┼──────────────┐
          ↓              ↓              ↓
     Classification  Credibility    Clustering
                         │
                         ↓
                PostgreSQL + PostGIS
                         ↓
                       FastAPI
                         ↓
                  React Dashboard
                         +
                    Admin Panel
```

---

# 16. Streaming Technology

## Apache Kafka

Kafka is the central event-streaming layer.

Proposed topics:

```text
weather.raw
citizen.raw
social.raw
government.raw

weather.processed
weather.events
weather.verified
```

Exact topic contracts are defined in:

`03_KAFKA_CONTRACT.md`

---

# 17. Stream Processing

## Apache Spark Structured Streaming

Spark is responsible for:

* Parsing
* Validation
* Transformation
* Cleaning
* Deduplication
* Aggregation
* Event processing
* Preparing data for downstream AI/storage

The MVP should demonstrate processing of at least:

> **1 million synthetic weather-event records**

where practical.

---

# 18. AI/ML Requirements

AI/ML is an assistive intelligence layer, not an absolute truth engine.

## 18.1 Event Classification

Input:

```text
Raw text/report
```

Output:

```text
Event category
Classification confidence
```

Example:

```text
"Heavy rainfall flooded roads in Mumbai"

→ flood
→ confidence: 0.94
```

---

# 19. Duplicate Detection

The system should identify potentially duplicate reports using combinations of:

* Text similarity (Jaccard/TF-IDF cosine)
* Timestamp proximity
* Geographic proximity
* Source information
* Content fingerprinting

Output:

```text
duplicate_score
```

Duplicate reports should not necessarily be permanently deleted.

They may be retained as supporting reports associated with the same event/cluster.

---

# 20. Event Clustering

Multiple reports describing the same real-world event should be grouped.

Example:

```text
20 reports
     ↓
Similar location
+
Similar time
+
Similar event
     ↓
1 Event Cluster
     +
20 Supporting Reports
```

This prevents the dashboard from treating every report as a separate disaster.

---

# 21. Source Trust Score

The system should maintain a source-level trust indicator.

Example:

```text
Source Trust Score: 75/100
```

This represents the historical/reliability characteristics of the source.

It is separate from the credibility of an individual event.

---

# 22. Event Credibility Score

Each applicable event may receive a credibility score.

Example:

```text
Credibility: 91/100
```

Possible factors:

* Source trust
* Number of independent reports
* Geographic consistency
* Temporal consistency
* Weather API correlation
* Contradictory evidence
* Duplicate/similarity signals

The system should present the score as an AI-assisted assessment rather than absolute proof.

---

# 23. Explainable Credibility

The dashboard should provide reasons behind a credibility score.

Example:

```text
Credibility: 94%

✓ 8 independent reports
✓ Reports within 2 km
✓ Reports within 15 minutes
✓ Weather API indicates heavy precipitation
✓ No major contradiction detected
```

---

# 24. Verification Status

Supported statuses:

```text
pending
verified
needs_review
suspicious
duplicate
```

New events default to `pending` until an admin acts.

Admin users can manually update verification status.

Manual verification is an important part of the system because AI output is not treated as absolute truth.

---

# 25. Storage Architecture

The platform uses multiple storage layers.

## 25.1 PostgreSQL + PostGIS

Primary operational/dashboard database.

Stores:

* Processed events
* Active events
* Important events
* Verified events
* Event clusters
* Locations
* AI results
* Verification actions
* Dashboard data

PostGIS is used for geographic/spatial operations.

---

# 26. Data Lake

The existing **1 TB HDD** is used for large-scale storage.

Potential contents:

```text
raw/
processed/
synthetic/
media/
logs/
```

Data may include:

* Raw JSON
* CSV
* Parquet
* Images
* Videos
* Synthetic datasets
* Logs

---

# 27. Parquet

Large historical datasets should preferably be stored in Parquet.

Example:

```text
weather_events_001.parquet
weather_events_002.parquet
weather_events_003.parquet
```

Parquet is intended for efficient analytical storage and integration with Spark.

---

# 28. DuckDB

DuckDB is optional.

It may be used for direct analytical querying of Parquet files.

```text
HDD
 ↓
Parquet
 ↓
DuckDB
 ↓
Historical Analytics
```

DuckDB is not a replacement for:

* PostgreSQL
* PostGIS
* Kafka
* Spark
* Object storage

It is an optional analytical engine.

---

# 29. Cloud Storage

Cloud storage is optional.

Cloudflare R2 may be used for:

* Selected demo datasets
* Small media samples
* Parquet files
* Cloud-accessible demonstration data

The project should not depend on a large paid cloud-storage requirement for the MVP.

The 1 TB HDD is the primary large-data storage option for the hackathon.

---

# 30. Backend

## FastAPI

FastAPI provides REST APIs between the frontend and backend systems.

Expected API areas:

```text
/api/v1/events
/api/v1/events/{id}
/api/v1/events/stats
/api/v1/events/map
/api/v1/citizen-reports
/api/v1/verification
/api/v1/health
/api/v1/auth/login
```

Exact endpoint definitions will be frozen in:

`04_API_CONTRACT.md`

---

# 31. Frontend

Technology:

* React
* Vite
* Tailwind CSS
* Leaflet or MapLibre
* Chart.js

The frontend contains:

1. Main Dashboard
2. Event Map
3. Event Table
4. Filters
5. Analytics
6. Event Details
7. Admin Panel

---

# 32. Dashboard Requirements

The dashboard must support:

### Required filters

* Date
* Event type
* Location
* Verification status

### Additional filters

* State
* District
* City
* Severity

---

# 33. Dashboard KPIs

Recommended KPI cards:

```text
Total Events
Verified Events
Needs Review
Suspicious Reports
Duplicate Reports
Active Event Clusters
```

---

# 34. Map

The dashboard must provide a geospatial visualization.

The MVP focuses on:

```text
Mumbai
Nagpur
Nashik
```

Event markers should indicate:

* Location
* Event category
* Severity
* Verification status

Selecting a marker should open event details.

---

# 35. Analytics

The dashboard should provide:

### Time analytics

Events per:

* Hour
* Day
* Selected date range

### Event analytics

Distribution by:

* Flood
* Rainfall
* Heatwave
* Thunderstorm
* etc.

### Location analytics

Compare:

* Mumbai
* Nagpur
* Nashik

### Verification analytics

Display:

* Verified
* Needs review
* Suspicious
* Duplicate

---

# 36. Admin Panel

The Admin Panel allows authorized users to:

* View reports
* View event details
* Review suspicious reports
* Verify reports
* Reject reports
* Mark duplicates
* View supporting evidence

Example:

```text
REPORT #R-2938

Event:
Flood

Location:
Mumbai

AI Classification:
Flood — 94%

Credibility:
71/100

Supporting Reports:
3

Weather Correlation:
Moderate

Status:
Needs Review

[VERIFY]
[REJECT]
[DUPLICATE]
```

Administrative actions should be recorded.

---

# 37. Real-Time Processing Target

The MVP aims for near-real-time processing.

Citizen-report target:

> Approximately <5 seconds from submission to dashboard availability under normal demo conditions.

Flow:

```text
Citizen
 ↓
FastAPI
 ↓
Kafka
 ↓
Spark
 ↓
AI/ML
 ↓
PostgreSQL
 ↓
Dashboard
```

Weather APIs may be polled periodically, such as every five minutes.

Exact intervals depend on API limitations.

---

# 38. Scalability Goal

The architecture must demonstrate that the system can handle large volumes.

MVP target:

> **1M+ synthetic records**

The system should demonstrate:

```text
Large Dataset
     ↓
Kafka
     ↓
Spark
     ↓
Processing
     ↓
Storage
     ↓
Analytics
```

The project should avoid claiming production-scale national capacity based solely on the five-day prototype.

---

# 39. Performance Philosophy

We prioritize:

1. Correctness
2. End-to-end functionality
3. Demonstrable scalability
4. Reliability
5. Performance optimization

We do not sacrifice a working end-to-end pipeline merely to optimize individual components.

---

# 40. Security and Privacy

The MVP should:

* Avoid storing unnecessary personal information
* Avoid exposing private citizen data publicly
* Validate API inputs
* Use environment variables for secrets
* Avoid hard-coded credentials
* Validate uploaded media
* Restrict Admin actions
* Separate configuration from code

Social-media/private-user information should not be unnecessarily replicated.

---

# 41. Error Handling

Every ingestion adapter should handle:

* Network failures
* Invalid responses
* Malformed data
* Missing fields
* Duplicate data
* API rate limits
* Temporary service failures

Failed records should be logged rather than silently discarded.

---

# 42. Observability

The MVP should provide basic:

* Application logs
* Kafka logs
* Processing logs
* Error logs
* Ingestion counts
* Processing counts

Useful metrics include:

```text
records_ingested
records_processed
records_failed
duplicates_detected
events_classified
events_verified
```

---

# 43. Technology Stack

## Frontend

```text
React
Vite
Tailwind CSS
Leaflet / MapLibre
Chart.js
```

## Backend

```text
Python
FastAPI
```

## Streaming

```text
Apache Kafka
Apache Spark Structured Streaming
```

## Database

```text
PostgreSQL
PostGIS
```

## AI/ML

```text
Python
numpy
Rule-based NLP (keyword dictionaries)
Optional embeddings (future scope)
```

## Data Formats

```text
JSON
CSV
Parquet
```

## Storage

```text
1 TB HDD
Optional Cloudflare R2
```

## Deployment

```text
Docker
Docker Compose
```

## Version Control

```text
GitHub
```

---

# 44. Team Structure

Six members:

## Member 1 — Architecture / DevOps / Integration

Responsibilities:

* Repository
* Docker
* Docker Compose
* Environment configuration
* Infrastructure
* Integration
* System testing

---

## Member 2 — Data Ingestion

Responsibilities:

* Weather API adapter
* RSS adapter
* Website adapter
* Social adapter
* Dataset loader
* Synthetic data generator
* Source normalization

---

## Member 3 — Kafka / Spark

Responsibilities:

* Kafka
* Kafka topics
* Producers
* Spark Structured Streaming
* Stream transformations
* Deduplication pipeline
* Aggregation

---

## Member 4 — AI/ML

Responsibilities:

* Event classification
* NLP
* Duplicate scoring
* Credibility scoring
* Source trust logic
* Event clustering
* Explainability

---

## Member 5 — Database / Backend

Responsibilities:

* PostgreSQL
* PostGIS
* Database schema
* FastAPI
* Event APIs
* Citizen report APIs
* Verification APIs

---

## Member 6 — Frontend

Responsibilities:

* React
* Dashboard
* Map
* Charts
* Filters
* Event details
* Admin Panel

---

# 45. Source-of-Truth Documents

The project must maintain the following documents:

```text
docs/
│
├── 00_MASTER_PROJECT_SPEC.md  (this document)
├── 01_ARCHITECTURE.md
├── 02_DATA_SCHEMA.md
├── 03_KAFKA_CONTRACT.md
├── 04_API_CONTRACT.md
├── 05_AI_ML_SPEC.md
├── 06_IMPLEMENTATION_PLAN.md
├── 07_DOCKER_DEPLOYMENT_SPEC.md
└── 08_TESTING_QA_SPEC.md
```

This document is the highest-level project contract.

---

# 46. Change Control

No member should independently change:

* Event schema
* Kafka topics
* API contracts
* Event categories
* Source types
* Database structure
* AI output structure

without updating the relevant Source-of-Truth document.

The project should prioritize contract compatibility over individual implementation preferences.

---

# 47. Five-Day MVP Plan

## Day 1 — Foundation

Goals:

* Repository
* Project structure
* Docker
* Kafka
* PostgreSQL/PostGIS
* Basic event schema
* Basic API
* Basic frontend
* One working ingestion path

Success criterion:

```text
One event
 ↓
Kafka
 ↓
Spark
 ↓
Database
 ↓
API
 ↓
Dashboard
```

---

## Day 2 — Data Pipeline

Implement:

* Weather API
* RSS
* Website adapter
* Social adapter/simulated feed
* Dataset loader
* Synthetic generator
* Kafka topics
* Spark pipeline

---

## Day 3 — Intelligence

Implement:

* Event classification
* Deduplication
* Credibility scoring
* Source trust
* Event clustering
* Verification logic

---

## Day 4 — Dashboard Integration

Implement:

* Real-time map
* Filters
* Analytics
* Event details
* Admin Panel
* Verification workflow
* Full backend/frontend integration

---

## Day 5 — Demo and Hardening

Perform:

* 1M+ synthetic-data test
* End-to-end testing
* Bug fixing
* Performance tuning
* Demo preparation
* Presentation
* Backup demo dataset
* Failure fallback

---

# 48. Out of Scope for MVP

The following must not consume significant development time during the five-day build:

* National-scale weather forecasting
* Replacement of IMD
* Full unrestricted social-media scraping
* Mobile application
* Satellite-image deep learning
* Kubernetes
* Blockchain
* Complex microservice architecture
* Full disaster-management ERP
* Production-grade national deployment
* Training large foundation models

These belong to future scope.

---

# 49. Expected System Outputs

The platform should produce:

### 1. Structured Weather Events

```text
Event
+
Location
+
Time
+
Category
+
Severity
+
Source
+
AI analysis
+
Verification
```

### 2. Real-Time Event Map

Shows where weather events are occurring.

### 3. Event Classification

Automatically identifies event types.

### 4. Duplicate Groups

Groups similar reports.

### 5. Event Clusters

Groups reports describing the same underlying event.

### 6. Credibility Scores

Provides AI-assisted credibility assessment.

### 7. Verification Status

```text
Verified
Needs Review
Suspicious
Duplicate
```

### 8. Historical Analytics

Provides trends and geographic/event analysis.

### 9. Admin Review Interface

Allows human verification and correction.

---

# 50. Expected Impact

The platform aims to provide:

### Faster information discovery

Multiple sources become available through a single system.

### Reduced information noise

Duplicate reports are identified and grouped.

### Better report assessment

Suspicious or low-confidence information can be prioritized for review.

### Improved geographic awareness

Events can be viewed spatially.

### Better historical analysis

Large datasets can be analyzed over time.

### Citizen-to-authority information flow

Ground-level citizen reports can become part of a structured weather intelligence system.

---

# 51. Core Demo Story

The final demonstration should follow a realistic event.

Example:

```text
Citizen reports flooding in Mumbai
            ↓
Citizen Web Form
            ↓
FastAPI
            ↓
Kafka
            ↓
Spark
            ↓
AI Classification
            ↓
"Flood — 94%"
            ↓
Weather API correlation
            ↓
Additional RSS/social reports
            ↓
Duplicate detection
            ↓
Event clustering
            ↓
Credibility Score
            ↓
PostgreSQL/PostGIS
            ↓
Real-Time Dashboard
            ↓
Admin Verification
            ↓
VERIFIED FLOOD EVENT
```

Then demonstrate:

```text
1,000,000+ synthetic records
             ↓
Kafka
             ↓
Spark
             ↓
Processing
             ↓
Analytics
```

---

# 52. Final Value Proposition

The platform converts:

> **Fragmented weather information**

into:

> **Structured, real-time, deduplicated, credibility-scored and geospatially actionable weather intelligence.**

The three central value pillars are:

## SPEED

Automated multi-source ingestion and near-real-time processing.

## TRUST

AI-assisted credibility assessment, source evaluation and duplicate detection.

## ACTIONABILITY

Geospatial event clusters, filters, analytics and human verification through one dashboard.

---

# 53. Final One-Line Description

> **A lightweight, open-source and replicable big-data weather intelligence platform that aggregates multi-source weather information, processes it in real time, detects and classifies weather events, assesses report credibility, removes duplicate noise, and delivers geospatial intelligence through a web dashboard and Admin Panel.**

---

# 54. Definition of MVP Success

The project is considered successful if, during the final demonstration, the team can show:

```text
✓ Multiple source types
✓ RSS ingestion
✓ Website ingestion
✓ Weather API ingestion
✓ Citizen reports
✓ Social-media adapter
✓ Synthetic 1M+ dataset
✓ Kafka streaming
✓ Spark processing
✓ AI event classification
✓ Duplicate detection
✓ Credibility scoring
✓ Event clustering
✓ PostgreSQL/PostGIS
✓ Parquet storage
✓ Real-time/near-real-time dashboard
✓ Geographic map
✓ Required filters
✓ Admin verification
✓ End-to-end working demo
```

The MVP does **not** need to prove that it can operate at India's full national production scale. It needs to demonstrate an architecture that is technically capable of scaling beyond the hackathon prototype.

---

## MASTER RULE

> **If a proposed feature does not directly contribute to demonstrating multi-source ingestion, big-data processing, AI-assisted weather-event intelligence, verification, geospatial analytics, or the official SIH26069 requirements, it should not be prioritized during the five-day MVP.**
