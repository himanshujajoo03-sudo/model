# 08 — Testing & QA Specification

**Project:** SIH26069 — National Weather Big Data Analytics Platform
**Document:** `08_TESTING_QA_SPEC.md`
**Version:** 1.0
**Status:** AWAITING APPROVAL
**Derived from:** `01_ARCHITECTURE.md` v1.3 + `02_DATA_SCHEMA.md` v1.1 + `03_KAFKA_CONTRACT.md` v1.0 + `04_API_CONTRACT.md` v1.0 + `05_AI_ML_SPEC.md` v1.0 + `06_IMPLEMENTATION_PLAN.md` v1.0 + `07_DOCKER_DEPLOYMENT_SPEC.md` v1.0
**Last updated:** 2026-09-01

---

## Change Control

This document defines tests against approved contracts. It does NOT modify
any contract. If a test reveals a contract contradiction, the contradiction
is reported — the contract is not silently changed.

---

## 1. Testing Strategy

### 1.1 Testing Pyramid

```
           ┌──────────┐
           │   E2E    │  ← 1 golden path (mandatory)
           │  (1-2)   │
          ┌┴──────────┴┐
          │ Integration │  ← 6-8 integration flows (mandatory)
          │   (6-8)     │
         ┌┴─────────────┴┐
         │  Component     │  ← per-service tests (mandatory)
         │    (15-25)     │
        ┌┴───────────────┴┐
        │    Unit Tests    │  ← ML, validation, schema (mandatory)
        │     (40-60)      │
       ┌┴─────────────────┴┐
       │  Contract Tests    │  ← schema/enum compliance (mandatory)
       │      (20-30)       │
       └────────────────────┘
```

### 1.2 Test Categories

| Category | Mandatory? | Count Target | Runs When |
|----------|-----------|-------------|-----------|
| Contract validation | **Yes** | 20–30 | Every commit |
| Unit tests (ML) | **Yes** | 40–60 | Every commit |
| Unit tests (validation) | **Yes** | 15–25 | Every commit |
| Component tests | **Yes** | 15–25 | Before integration |
| Integration tests | **Yes** | 6–8 | After integration |
| End-to-end golden path | **Yes** | 1 | Before demo |
| Failure/recovery tests | **Yes** | 8–12 | Before demo |
| Data validation tests | **Yes** | 10–15 | After data load |
| Performance/load tests | Optional | 3–5 | Day 5 if time permits |
| Frontend smoke tests | **Yes** | 10 | Before demo |
| Security QA | **Yes** | 8–10 | Before demo |
| Docker QA | **Yes** | 1 | Every fresh clone |

### 1.3 Test Execution Order

```
1. Contract tests          (no infrastructure needed)
2. Unit tests              (no infrastructure needed)
3. Docker startup          (infrastructure up)
4. Component tests         (per-service)
5. Integration tests       (cross-service)
6. Data validation         (after data flows)
7. Failure tests           (deliberate breakage)
8. Frontend smoke          (visual verification)
9. Golden path E2E         (full pipeline)
10. Security QA            (pre-demo audit)
11. Performance (optional) (if time permits)
```

---

## 2. Contract Validation Tests

These tests verify code matches the approved specifications without
requiring running infrastructure.

### 2.1 Enum Compliance

| # | Test | Input | Expected | Contract |
|---|------|-------|---------|----------|
| C-01 | Valid source types | Any of: `weather_api`, `rss`, `website`, `social`, `simulated_social`, `government_dataset`, `citizen`, `synthetic` | PASS | `02_DATA_SCHEMA.md §1.1` |
| C-02 | Invalid source type | `"twitter_scrape"` | REJECT | `02_DATA_SCHEMA.md §1.1` |
| C-03 | Invalid source type | `""` (empty) | REJECT | `02_DATA_SCHEMA.md §1.1` |
| C-04 | Valid event categories | Any of: `rainfall`, `heavy_rainfall`, `flood`, `thunderstorm`, `lightning`, `heatwave`, `fog`, `dust_storm`, `strong_wind`, `hailstorm`, `cyclone`, `other` | PASS | `02_DATA_SCHEMA.md §1.2` |
| C-05 | Invalid event category | `"earthquake"` | REJECT | `02_DATA_SCHEMA.md §1.2` |
| C-06 | Valid severity values | `low`, `moderate`, `high`, `extreme` | PASS | `02_DATA_SCHEMA.md §1.3` |
| C-07 | Invalid severity | `"catastrophic"` | WARN → null | `02_DATA_SCHEMA.md §1.3` |
| C-08 | Valid verification status | `pending`, `verified`, `needs_review`, `suspicious`, `duplicate` | PASS | `02_DATA_SCHEMA.md §1.4` |
| C-09 | Invalid verification status | `"approved"` | REJECT | `02_DATA_SCHEMA.md §1.4` |

### 2.2 Required Field Tests

| # | Test | Input | Expected | Contract |
|---|------|-------|---------|----------|
| C-10 | Missing `event_id` | `null` | REJECT | `02_DATA_SCHEMA.md §3.1` |
| C-11 | Invalid `event_id` | `"not-a-uuid"` | REJECT | `02_DATA_SCHEMA.md §3.1` |
| C-12 | Missing `source_id` | `null` | REJECT | `02_DATA_SCHEMA.md §3.1` |
| C-13 | Empty `source_name` | `""` | REJECT | `02_DATA_SCHEMA.md §3.1` |
| C-14 | Missing `source_type` | `null` | REJECT | `02_DATA_SCHEMA.md §3.1` |
| C-15 | Missing `timestamp` | `null` | REJECT | `02_DATA_SCHEMA.md §3.1` |
| C-16 | Missing `ingestion_timestamp` | `null` | REJECT | `02_DATA_SCHEMA.md §3.1` |
| C-17 | Missing `location.country` | `null` | REJECT | `02_DATA_SCHEMA.md §3.2` |
| C-18 | Missing `event.category` | `null` | REJECT | `02_DATA_SCHEMA.md §3.3` |
| C-19 | Missing both lat/lon and city | All location fields null | REJECT | `02_DATA_SCHEMA.md §3.2` |

### 2.3 Timestamp Tests

| # | Test | Input | Expected | Contract |
|---|------|-------|---------|----------|
| C-20 | Valid UTC timestamp | `"2026-08-31T14:30:00.000Z"` | PASS | `02_DATA_SCHEMA.md §4` |
| C-21 | Valid offset timestamp | `"2026-08-31T20:00:00.000+05:30"` | PASS | `02_DATA_SCHEMA.md §4` |
| C-22 | Invalid space separator | `"2026-08-31 14:30:00"` | REJECT | `02_DATA_SCHEMA.md §4` |
| C-23 | Invalid Unix timestamp | `1725110400` | REJECT | `02_DATA_SCHEMA.md §4` |
| C-24 | Future timestamp (>5 min) | Current time + 10 minutes | REJECT | `02_DATA_SCHEMA.md §11` |
| C-25 | Timestamp before 2000 | `"1999-12-31T23:59:59Z"` | REJECT | `02_DATA_SCHEMA.md §11` |

### 2.4 Coordinate Tests

| # | Test | Input | Expected | Contract |
|---|------|-------|---------|----------|
| C-26 | Valid coordinates | lat=19.076, lon=72.878 | PASS | `02_DATA_SCHEMA.md §3.2` |
| C-27 | Latitude out of range | lat=91.0 | REJECT | `02_DATA_SCHEMA.md §11` |
| C-28 | Longitude out of range | lon=181.0 | REJECT | `02_DATA_SCHEMA.md §11` |
| C-29 | Lat without lon | lat=19.076, lon=null | REJECT | `02_DATA_SCHEMA.md §3.2` |
| C-30 | City alone (no coords) | city="Mumbai", lat=null, lon=null | PASS | `02_DATA_SCHEMA.md §3.2` |

### 2.5 Kafka Envelope Tests

| # | Test | Input | Expected | Contract |
|---|------|-------|---------|----------|
| C-31 | Valid envelope | All fields present, `event_type="weather_event"` | PASS | `03_KAFKA_CONTRACT.md §3` |
| C-32 | Missing `schema_version` | Field absent | REJECT | `03_KAFKA_CONTRACT.md §3.2` |
| C-33 | Missing `message_id` | Field absent | REJECT | `03_KAFKA_CONTRACT.md §3.2` |
| C-34 | Unknown `event_type` | `"unknown_type"` | REJECT | `03_KAFKA_CONTRACT.md §3.3` |
| C-35 | Unknown `schema_version` major | `"99.0"` | REJECT | `03_KAFKA_CONTRACT.md §12` |
| C-36 | Valid verification envelope | `event_type="verification_action"` | PASS | `03_KAFKA_CONTRACT.md §6.1` |
| C-37 | Missing envelope wrapper | Raw Canonical Event without envelope | REJECT | `03_KAFKA_CONTRACT.md §3.1` |

### 2.6 API Schema Tests

| # | Test | Input | Expected | Contract |
|---|------|-------|---------|----------|
| C-38 | Valid GET /events response | Contains `items`, `page`, `page_size`, `total`, `total_pages` | PASS | `04_API_CONTRACT.md §4.4` |
| C-39 | Valid error response | Contains `error.code`, `error.message`, `error.timestamp` | PASS | `04_API_CONTRACT.md §5` |
| C-40 | Valid health response | Contains `status`, `database`, `kafka`, `timestamp` | PASS | `04_API_CONTRACT.md §6` |
| C-41 | Valid event list item | Contains `event_id`, `event_timestamp`, `event_category`, etc. | PASS | `04_API_CONTRACT.md §8` |
| C-42 | Valid map event | Contains `event_id`, `latitude`, `longitude`, `event_category` | PASS | `04_API_CONTRACT.md §11` |

---

## 3. Canonical Event Tests

### 3.1 Valid Events (Per Source)

| # | Source | Key Fields | Expected |
|---|--------|-----------|----------|
| V-01 | Open-Meteo | `source_type="weather_api"`, valid coords, constructed description | PASS; produces to `weather.raw` |
| V-02 | RSS | `source_type="rss"`, `source_url` set, NLP-extracted category | PASS; produces to `weather.raw` |
| V-03 | Website | `source_type="website"`, allowlisted URL, scraped text | PASS; produces to `weather.raw` |
| V-04 | Simulated social | `source_type="simulated_social"`, `platform="simulated"` | PASS; produces to `social.raw` |
| V-05 | Government dataset | `source_type="government_dataset"`, file-sourced | PASS; produces to `government.raw` |
| V-06 | Citizen | `source_type="citizen"`, `source_name="citizen_form"`, form fields | PASS; produces to `citizen.raw` |
| V-07 | Synthetic | `source_type="synthetic"`, `source_name` contains `"synthetic"` | PASS; produces to `weather.raw` |

### 3.2 Invalid Events (REJECT)

| # | Defect | Input | Expected | Rule |
|---|--------|-------|---------|------|
| I-01 | Invalid UUID | `event_id="not-a-uuid"` | REJECT → dead-letter | `02_DATA_SCHEMA.md §11` |
| I-02 | Invalid source type | `source_type="twitter_scrape"` | REJECT → dead-letter | `02_DATA_SCHEMA.md §11` |
| I-03 | Missing source name | `source_name=""` | REJECT → dead-letter | `02_DATA_SCHEMA.md §11` |
| I-04 | Invalid category | `event.category="earthquake"` | REJECT → dead-letter | `02_DATA_SCHEMA.md §11` |
| I-05 | Invalid severity | `event.severity="catastrophic"` | WARN → nullify; event continues | `02_DATA_SCHEMA.md §11` |
| I-06 | Invalid timestamp format | `"31-08-2026 08:15"` | REJECT → dead-letter | `02_DATA_SCHEMA.md §11` |
| I-07 | Future timestamp | Current + 10 min | REJECT → dead-letter | `02_DATA_SCHEMA.md §11` |
| I-08 | Missing location | All location fields null | REJECT → dead-letter | `02_DATA_SCHEMA.md §11` |
| I-09 | Invalid latitude | `latitude=91.0` | REJECT → dead-letter | `02_DATA_SCHEMA.md §11` |
| I-10 | Invalid longitude | `longitude=181.0` | REJECT → dead-letter | `02_DATA_SCHEMA.md §11` |
| I-11 | Oversized description | >2000 characters | WARN → truncate to 2000; event continues | `02_DATA_SCHEMA.md §11` |
| I-12 | Missing country | `location.country=null` | REJECT → dead-letter | `02_DATA_SCHEMA.md §11` |
| I-13 | Out-of-range trust score | `source_trust_score=1.5` | WARN → nullify; event continues | `02_DATA_SCHEMA.md §11` |

### 3.3 Warning Events (Auto-Fix)

| # | Defect | Input | Expected | Rule |
|---|--------|-------|---------|------|
| W-01 | Missing verification status | `verification.status=null` | AUTO-FIX → `"pending"` | `02_DATA_SCHEMA.md §11` |
| W-02 | Synthetic without "synthetic" in name | `source_type="synthetic"`, `source_name="test_gen"` | WARN logged | `02_DATA_SCHEMA.md §11` |
| W-03 | Simulated social without platform | `source_type="simulated_social"`, `platform=null` | WARN logged | `02_DATA_SCHEMA.md §11` |

---

## 4. Kafka Tests

### 4.1 Topic Configuration

| # | Test | Expected | Contract |
|---|------|---------|----------|
| K-01 | `weather.raw` exists with 1 partition | Topic exists; partition count = 1 | `03_KAFKA_CONTRACT.md §2.2` |
| K-02 | `citizen.raw` exists | Topic exists | `03_KAFKA_CONTRACT.md §2.2` |
| K-03 | `social.raw` exists | Topic exists | `03_KAFKA_CONTRACT.md §2.2` |
| K-04 | `government.raw` exists | Topic exists | `03_KAFKA_CONTRACT.md §2.2` |
| K-05 | `weather.processed` exists | Topic exists | `03_KAFKA_CONTRACT.md §2.2` |
| K-06 | `weather.events` exists | Topic exists | `03_KAFKA_CONTRACT.md §2.2` |
| K-07 | `weather.verified` exists | Topic exists | `03_KAFKA_CONTRACT.md §2.2` |
| K-08 | No undocumented topics | Exactly 7 topics total | `03_KAFKA_CONTRACT.md §2.1` |

### 4.2 Producer/Consumer Tests

| # | Test | Expected | Contract |
|---|------|---------|----------|
| K-09 | Ingestion produces to `weather.raw` | Valid Canonical Event in envelope | `01_ARCHITECTURE.md §9` |
| K-10 | API produces to `citizen.raw` | Valid Canonical Event in envelope | `01_ARCHITECTURE.md §9` |
| K-11 | Ingestion produces to `social.raw` | Valid Canonical Event in envelope | `01_ARCHITECTURE.md §9` |
| K-12 | Ingestion produces to `government.raw` | Valid Canonical Event in envelope | `01_ARCHITECTURE.md §9` |
| K-13 | Spark produces to `weather.events` | Enriched event with `ai.*` populated | `03_KAFKA_CONTRACT.md §5.4` |
| K-14 | API produces to `weather.verified` | Verification action payload | `03_KAFKA_CONTRACT.md §6.1` |
| K-15 | Spark consumes from all 4 raw topics | Events processed from `weather.raw`, `citizen.raw`, `social.raw`, `government.raw` | `03_KAFKA_CONTRACT.md §9.1` |
| K-16 | PG Writer consumes from `weather.events` only | Writer does NOT consume `weather.processed` | `03_KAFKA_CONTRACT.md §2.2` |

### 4.3 Envelope and Key Tests

| # | Test | Expected | Contract |
|---|------|---------|----------|
| K-17 | All messages wrapped in envelope | `schema_version`, `message_id`, `event_type`, `produced_at`, `producer`, `payload` present | `03_KAFKA_CONTRACT.md §3.1` |
| K-18 | Message key is `event_id` | Kafka key matches `event_id` in payload | `03_KAFKA_CONTRACT.md §7.1` |
| K-19 | Malformed JSON to Kafka | Consumer logs error; message not consumed; pipeline continues | `03_KAFKA_CONTRACT.md §11.2` |
| K-20 | Unknown envelope `schema_version` | Consumer rejects; logs warning | `03_KAFKA_CONTRACT.md §12.2` |

### 4.4 Consumer Group Tests

| # | Test | Expected | Contract |
|---|------|---------|----------|
| K-21 | Spark consumer group is `spark-processing` | Group ID matches | `03_KAFKA_CONTRACT.md §9.1` |
| K-22 | PG Writer consumer group is `postgres-writer` | Group ID matches | `03_KAFKA_CONTRACT.md §9.1` |
| K-23 | `weather.processed` has no active consumer | Topic retains messages but none consumed in production | `03_KAFKA_CONTRACT.md §2.2` |

---

## 5. Spark Tests

### 5.1 Processing Pipeline

| # | Test | Input | Expected | Contract |
|---|------|-------|---------|----------|
| S-01 | Valid event passes validation | Complete Canonical Event | Event passes; no dead-letter | `02_DATA_SCHEMA.md §11` |
| S-02 | Invalid event is rejected | Event with invalid UUID | Written to dead-letter; pipeline continues | `02_DATA_SCHEMA.md §11` |
| S-03 | Warning event continues | Event with oversized description | Description truncated; event continues | `02_DATA_SCHEMA.md §11` |
| S-04 | Timestamp normalisation | Timestamp with `+05:30` offset | Converted to UTC `Z` format | `03_KAFKA_CONTRACT.md §5.2` |
| S-05 | Missing `verification.status` | `verification.status=null` | Auto-fixed to `"pending"` | `02_DATA_SCHEMA.md §11` |
| S-06 | Null severity preserved | `event.severity=null` | Passed through as null | `02_DATA_SCHEMA.md §11` |

### 5.2 ML Enrichment

| # | Test | Expected | Contract |
|---|------|---------|----------|
| S-07 | `ai.classified_category` populated | Valid enum value from §1.2 | `05_AI_ML_SPEC.md §4.1` |
| S-08 | `ai.classification_confidence` populated | Float 0.0–1.0 | `05_AI_ML_SPEC.md §7` |
| S-09 | `ai.credibility_score` populated | Float 0.0–1.0 | `05_AI_ML_SPEC.md §8` |
| S-10 | `ai.credibility_reasons` populated | Non-empty string list | `05_AI_ML_SPEC.md §15` |
| S-11 | `ai.duplicate_score` populated | Float 0.0–1.0 | `05_AI_ML_SPEC.md §11` |
| S-12 | `ai.cluster_id` populated or null | UUID v4 or null | `05_AI_ML_SPEC.md §13` |
| S-13 | ML failure does not drop event | Exception in any ML function | Event proceeds with null ML outputs | `05_AI_ML_SPEC.md §24` |

### 5.3 Output Validation

| # | Test | Expected | Contract |
|---|------|---------|----------|
| S-14 | Output to `weather.events` matches enriched schema | All Canonical Event fields + `ai.*` populated | `03_KAFKA_CONTRACT.md §5.4` |
| S-15 | `event.category` NOT modified by ML | Adapter's category preserved; ML writes to `ai.classified_category` | `02_DATA_SCHEMA.md §3.3` |
| S-16 | `verification.status` NOT modified by ML | Remains `"pending"` | `02_DATA_SCHEMA.md §3.7` |
| S-17 | Kafka key remains `event_id` | Key unchanged from input | `03_KAFKA_CONTRACT.md §7.1` |

---

## 6. ML Tests

Per `05_AI_ML_SPEC.md` exactly.

### 6.1 Classification Tests

| # | Test | Input Description | Expected Category | Min Confidence |
|---|------|------------------|-------------------|----------------|
| M-01 | Rainfall | "Light rain showers in Mumbai" | `rainfall` | ≥ 0.40 |
| M-02 | Heavy rainfall | "Very heavy rainfall in Nashik, roads submerged" | `heavy_rainfall` | ≥ 0.60 |
| M-03 | Flood | "Waterlogged streets, inundated areas, flash flood" | `flood` | ≥ 0.60 |
| M-04 | Thunderstorm | "Thunder and lightning storm overnight" | `thunderstorm` or `lightning` | ≥ 0.50 |
| M-05 | Lightning | "Lightning strike damaged power lines" | `lightning` | ≥ 0.50 |
| M-06 | Heatwave | "43°C temperature recorded, extreme heat warning" | `heatwave` | ≥ 0.60 |
| M-07 | Fog | "Dense fog reducing visibility to 50 metres" | `fog` | ≥ 0.60 |
| M-08 | Dust storm | "Dust storm with sandy winds across the region" | `dust_storm` | ≥ 0.50 |
| M-09 | Strong wind | "Gale-force winds gusting at 80 km/h" | `strong_wind` | ≥ 0.50 |
| M-10 | Hailstorm | "Hailstones damaged crops in Nashik district" | `hailstorm` | ≥ 0.60 |
| M-11 | Cyclone | "Very severe cyclonic storm approaching coast" | `cyclone` | ≥ 0.60 |
| M-12 | Other | "Unusual weather pattern observed, no specific event" | `other` | Any |
| M-13 | Empty description | `""` | Falls back to category hint | ≥ 0.20 |
| M-14 | Hindi keywords | "भारी बारिश से बाढ़" | `heavy_rainfall` or `flood` | ≥ 0.40 |
| M-15 | Marathi keywords | "मुसळधार पाऊस" | `heavy_rainfall` | ≥ 0.40 |

### 6.2 Confidence Tests

| # | Test | Expected | Contract |
|---|------|---------|----------|
| M-16 | Confidence in range | All outputs: 0.0 ≤ confidence ≤ 1.0 | `05_AI_ML_SPEC.md §7.1` |
| M-17 | High confidence threshold | Multiple keyword hits + structured data → ≥ 0.80 | `05_AI_ML_SPEC.md §7.2` |
| M-18 | Low confidence fallback | No keywords + no hint → < 0.40 | `05_AI_ML_SPEC.md §7.2` |

### 6.3 Credibility Tests

| # | Test | Expected | Contract |
|---|------|---------|----------|
| M-19 | High-trust source | `source_type="weather_api"` → credibility ≥ 0.70 | `05_AI_ML_SPEC.md §9.1` |
| M-20 | Low-trust source | `source_type="social"` → credibility ≤ 0.65 | `05_AI_ML_SPEC.md §9.1` |
| M-21 | Corroborated event | 3 independent reports → credibility ≥ 0.75 | `05_AI_ML_SPEC.md §10` |
| M-22 | No corroboration | Single report → credibility based on other factors only | `05_AI_ML_SPEC.md §10` |
| M-23 | Weather agreement | API confirms heavy rain + citizen flood report → weather_factor ≥ 0.80 | `05_AI_ML_SPEC.md §8.3` |
| M-24 | No weather data | No API data available → weather_factor = 0.30 (neutral) | `05_AI_ML_SPEC.md §8.3` |
| M-25 | Reasons are honest | If no corroboration exists, reason states "No independent corroborating reports" | `05_AI_ML_SPEC.md §15.1` |

### 6.4 Duplicate Detection Tests

| # | Test | Expected | Contract |
|---|------|---------|----------|
| M-26 | Exact duplicate | Same text, same time, same location → duplicate_score ≥ 0.85 | `05_AI_ML_SPEC.md §12.1` |
| M-27 | Near duplicate | Slight rewording, same time/location → duplicate_score ≥ 0.70 | `05_AI_ML_SPEC.md §12.1` |
| M-28 | Same source ID | Same `source_id` → duplicate_score ≥ 0.80 | `05_AI_ML_SPEC.md §11.4` |
| M-29 | Unrelated events | Different description, different location → duplicate_score < 0.30 | `05_AI_ML_SPEC.md §12.1` |
| M-30 | No recent events | Empty recent events list → duplicate_score = 0.0 | `05_AI_ML_SPEC.md §11.6` |

### 6.5 Clustering Tests

| # | Test | Expected | Contract |
|---|------|---------|----------|
| M-31 | Same location + time | Within 3 km, 30 min, same category → same cluster | `05_AI_ML_SPEC.md §13.3` |
| M-32 | Outside radius | >3 km apart → different cluster | `05_AI_ML_SPEC.md §13.3` |
| M-33 | Outside time window | >30 min apart → different cluster | `05_AI_ML_SPEC.md §13.3` |
| M-34 | Incompatible category | Same location/time but heatwave vs flood → different cluster | `05_AI_ML_SPEC.md §13.2` |
| M-35 | No matching cluster | First event in area → `cluster_id = null` | `05_AI_ML_SPEC.md §13.4` |

### 6.6 Explainability Tests

| # | Test | Expected | Contract |
|---|------|---------|----------|
| M-36 | Reasons are non-empty | Always ≥ 1 reason string | `05_AI_ML_SPEC.md §15` |
| M-37 | Reasons match factors | Generated reasons correspond to actual computed factor values | `05_AI_ML_SPEC.md §15.2` |
| M-38 | No fabricated evidence | If no corroboration → reason says so; does NOT claim corroboration exists | `05_AI_ML_SPEC.md §15.1` |

---

## 7. PostgreSQL/PostGIS Tests

| # | Test | Expected | Contract |
|---|------|---------|----------|
| DB-01 | Event insertion | `INSERT` succeeds; row appears in `events` table | `02_DATA_SCHEMA.md §6.1` |
| DB-02 | Field mapping correct | JSON `location.latitude` → DB `latitude`; `event.category` → `event_category` | `02_DATA_SCHEMA.md §6 preamble` |
| DB-03 | Geometry auto-created | After insert with lat/lon, `geom` column is non-null | `02_DATA_SCHEMA.md §9` |
| DB-04 | Latitude/longitude correctness | `ST_X(geom)` = longitude; `ST_Y(geom)` = latitude (NOT swapped) | `02_DATA_SCHEMA.md §9` |
| DB-05 | SRID is 4326 | `ST_SRID(geom) = 4326` | `02_DATA_SCHEMA.md §9` |
| DB-06 | All 11 indexes exist | `SELECT count(*) FROM pg_indexes WHERE tablename='events'` ≥ 11 | `02_DATA_SCHEMA.md §8` |
| DB-07 | Cluster FK works | Insert event with valid `cluster_id` → succeeds | `02_DATA_SCHEMA.md §6.1` |
| DB-08 | Cluster FK invalid | Insert event with non-existent `cluster_id` → fails (FK constraint) | `02_DATA_SCHEMA.md §6.1` |
| DB-09 | Verification log insertion | Insert into `verification_log` with valid `event_id` → succeeds | `02_DATA_SCHEMA.md §6.5` |
| DB-10 | Verification log cascade | Delete event → `verification_log` rows cascade-delete | `02_DATA_SCHEMA.md §6.5` |
| DB-11 | Duplicate insertion idempotent | `INSERT ... ON CONFLICT (event_id) DO UPDATE` → no duplicate row | `03_KAFKA_CONTRACT.md §10.2` |
| DB-12 | Timestamps stored as TIMESTAMPTZ | `pg_typeof(event_timestamp) = 'timestamp with time zone'` | `02_DATA_SCHEMA.md §6.1` |
| DB-13 | `set_updated_at` trigger fires | `UPDATE events ...` → `updated_at` changes | `02_DATA_SCHEMA.md §6.3` |
| DB-14 | CHECK constraints active | Insert invalid `source_type` → fails | `02_DATA_SCHEMA.md §6.1` |
| DB-15 | Seed data present | `SELECT count(*) FROM sources` ≥ 2 | `06_IMPLEMENTATION_PLAN.md §9` |

---

## 8. FastAPI Tests

### 8.1 `GET /api/v1/health`

| # | Test | Expected | Contract |
|---|------|---------|----------|
| A-01 | Healthy state | 200; `status="healthy"`, `database="connected"`, `kafka="connected"` | `04_API_CONTRACT.md §6` |
| A-02 | DB unavailable | 503; `status="unhealthy"`, `database="unavailable"` | `04_API_CONTRACT.md §6` |

### 8.2 `GET /api/v1/events`

| # | Test | Expected | Contract |
|---|------|---------|----------|
| A-03 | Default request | 200; paginated list with `items`, `page`, `total` | `04_API_CONTRACT.md §8` |
| A-04 | With `city` filter | 200; only events matching city | `04_API_CONTRACT.md §4.5` |
| A-05 | With `category` filter | 200; only events matching category | `04_API_CONTRACT.md §4.5` |
| A-06 | With `start_time`/`end_time` | 200; events within time range | `04_API_CONTRACT.md §4.5` |
| A-07 | With `min_credibility` | 200; events above threshold | `04_API_CONTRACT.md §4.5` |
| A-08 | Empty result | 200; `items=[]`, `total=0` | `04_API_CONTRACT.md §4.4` |
| A-09 | Invalid enum value in filter | 400; `INVALID_ENUM_VALUE` error | `04_API_CONTRACT.md §5.2` |
| A-10 | Pagination: page 2 | 200; correct offset | `04_API_CONTRACT.md §4.4` |

### 8.3 `GET /api/v1/events/{event_id}`

| # | Test | Expected | Contract |
|---|------|---------|----------|
| A-11 | Valid event ID | 200; full event with nested structure + verification history | `04_API_CONTRACT.md §9` |
| A-12 | Invalid UUID format | 400; `INVALID_UUID` | `04_API_CONTRACT.md §5.2` |
| A-13 | Non-existent event ID | 404; `EVENT_NOT_FOUND` | `04_API_CONTRACT.md §5.2` |

### 8.4 `GET /api/v1/events/stats`

| # | Test | Expected | Contract |
|---|------|---------|----------|
| A-14 | Default stats | 200; `total_events`, `by_category`, `by_severity`, `by_city`, etc. | `04_API_CONTRACT.md §10` |
| A-15 | With time filter | 200; filtered stats | `04_API_CONTRACT.md §10` |
| A-16 | Stats match manual count | `total_events` matches `SELECT count(*)` | `04_API_CONTRACT.md §10` |

### 8.5 `GET /api/v1/events/map`

| # | Test | Expected | Contract |
|---|------|---------|----------|
| A-17 | Valid bounding box | 200; events within bbox with coordinates | `04_API_CONTRACT.md §11` |
| A-18 | Invalid coordinates | 400; `INVALID_COORDINATES` | `04_API_CONTRACT.md §5.2` |
| A-19 | Empty bbox | 200; `events=[]`, `count=0` | `04_API_CONTRACT.md §11` |

### 8.6 `POST /api/v1/citizen-reports`

| # | Test | Expected | Contract |
|---|------|---------|----------|
| A-20 | Valid submission | 201; `event_id` returned | `04_API_CONTRACT.md §12` |
| A-21 | Missing required field | 400; `MISSING_REQUIRED_FIELD` | `04_API_CONTRACT.md §12` |
| A-22 | Invalid category | 400; `INVALID_ENUM_VALUE` | `04_API_CONTRACT.md §12` |
| A-23 | Invalid coordinates | 400; `INVALID_COORDINATES` | `04_API_CONTRACT.md §12` |
| A-24 | Kafka unavailable | 503; `KAFKA_UNAVAILABLE` | `04_API_CONTRACT.md §12` |

### 8.7 `POST /api/v1/verification`

| # | Test | Expected | Contract |
|---|------|---------|----------|
| A-25 | Valid verify action (with JWT) | 200; `verification_status` updated | `04_API_CONTRACT.md §14` |
| A-26 | No JWT token | 401; `UNAUTHORIZED` | `04_API_CONTRACT.md §3.2` |
| A-27 | Expired JWT | 401; `TOKEN_EXPIRED` | `04_API_CONTRACT.md §5.2` |
| A-28 | Invalid action value | 400; `INVALID_ENUM_VALUE` | `04_API_CONTRACT.md §14` |
| A-29 | Non-existent event ID | 404; `EVENT_NOT_FOUND` | `04_API_CONTRACT.md §14` |
| A-30 | All 4 actions work | `verified`, `rejected`, `marked_suspicious`, `marked_duplicate` | `02_DATA_SCHEMA.md §1.4` |

### 8.8 `POST /api/v1/auth/login`

| # | Test | Expected | Contract |
|---|------|---------|----------|
| A-31 | Valid credentials | 200; `access_token`, `token_type="bearer"` | `04_API_CONTRACT.md §15` |
| A-32 | Invalid credentials | 401; `UNAUTHORIZED` | `04_API_CONTRACT.md §15` |
| A-33 | Missing fields | 400; `MISSING_REQUIRED_FIELD` | `04_API_CONTRACT.md §15` |

---

## 9. Citizen Report Tests

### 9.1 Full Flow

| # | Test | Steps | Expected | Contract |
|---|------|-------|---------|----------|
| CR-01 | Happy path | Form → API → `citizen.raw` → Spark → ML → `weather.events` → PG → DB → GET /events | Event visible in dashboard within ~5 sec | `01_ARCHITECTURE.md §4` |
| CR-02 | Invalid form data | Submit with missing city + missing coordinates | 400 error; no Kafka message | `04_API_CONTRACT.md §12` |
| CR-03 | Missing coordinates, city present | Submit with city="Mumbai", no lat/lon | 201; event accepted | `02_DATA_SCHEMA.md §3.2` |
| CR-04 | With photo upload | Submit with attached image | 201; photo URL in `media.photos` | `04_API_CONTRACT.md §13` |
| CR-05 | Oversized photo | Submit with 10MB image | 400; `MEDIA_TOO_LARGE` | `04_API_CONTRACT.md §13` |
| CR-06 | Invalid file type | Submit with `.exe` file | 400; `MEDIA_INVALID_TYPE` | `04_API_CONTRACT.md §13` |
| CR-07 | Malformed JSON body | Send invalid JSON | 400; `INVALID_JSON` | `04_API_CONTRACT.md §5.2` |

### 9.2 Verification Chain

| # | Test | Expected | Contract |
|---|------|---------|----------|
| CR-08 | Citizen event has `source_type="citizen"` | Verified in DB row | `02_DATA_SCHEMA.md §1.1` |
| CR-09 | Citizen event has `source_name="citizen_form"` | Verified in DB row | `02_DATA_SCHEMA.md §12` |
| CR-10 | Citizen event starts as `verification.status="pending"` | Verified in DB row | `02_DATA_SCHEMA.md §3.7` |

---

## 10. Admin Verification Tests

### 10.1 Full Flow

| # | Test | Steps | Expected | Contract |
|---|------|-------|---------|----------|
| AV-01 | Verify action | Login → POST /verification with `action="verified"` | Event `verification_status="verified"` in DB | `04_API_CONTRACT.md §14` |
| AV-02 | Reject action | Login → POST /verification with `action="rejected"` | Event status updated; log entry created | `04_API_CONTRACT.md §14` |
| AV-03 | Mark suspicious | Login → POST /verification with `action="marked_suspicious"` | Event `verification_status="suspicious"` | `04_API_CONTRACT.md §14` |
| AV-04 | Mark duplicate | Login → POST /verification with `action="marked_duplicate"` | Event `verification_status="duplicate"` | `04_API_CONTRACT.md §14` |
| AV-05 | Verification log created | After any action, query `verification_log` | Row exists with correct `action`, `performed_by`, `performed_at` | `02_DATA_SCHEMA.md §6.5` |
| AV-06 | Kafka message produced | After action, check `weather.verified` topic | Verification action message with correct payload | `03_KAFKA_CONTRACT.md §6` |
| AV-07 | Without auth | POST /verification without JWT | 401; no DB change | `04_API_CONTRACT.md §3.2` |
| AV-08 | Duplicate action on same event | Verify same event twice | Second verification log entry; event status updated again | `02_DATA_SCHEMA.md §6.5` |

---

## 11. Frontend Tests

### 11.1 Mandatory Smoke Tests

| # | Test | Expected | Contract |
|---|------|---------|----------|
| FE-01 | Dashboard loads | Page renders without JS errors | `01_ARCHITECTURE.md §3` |
| FE-02 | KPI cards display | Numbers visible; match API `/events/stats` | `04_API_CONTRACT.md §10` |
| FE-03 | Map loads | Leaflet map renders; tiles load | `01_ARCHITECTURE.md §3` |
| FE-04 | Event markers appear | Markers at correct coordinates for available events | `04_API_CONTRACT.md §11` |
| FE-05 | Filters work | Selecting city/category updates event list | `04_API_CONTRACT.md §4.5` |
| FE-06 | Event table loads | Table rows displayed; pagination works | `04_API_CONTRACT.md §8` |
| FE-07 | Event details open | Clicking event shows full detail page | `04_API_CONTRACT.md §9` |
| FE-08 | AI explanation appears | Detail page shows `ai.*` fields: classification, credibility, reasons | `05_AI_ML_SPEC.md §16` |
| FE-09 | Citizen form submits | Fill form → submit → 201 response → event appears in pipeline | `04_API_CONTRACT.md §12` |
| FE-10 | Admin login works | Enter credentials → receive token → verification actions enabled | `04_API_CONTRACT.md §15` |
| FE-11 | Admin verify works | Click verify → event status changes → visible on dashboard | `04_API_CONTRACT.md §14` |
| FE-12 | Synthetic data labelled | Events with `source_type="synthetic"` show "Synthetic" label | `01_ARCHITECTURE.md §12` |

---

## 12. End-to-End Golden Path

### 12.1 The One Mandatory Test

```
Open-Meteo API
  → weather.raw (Kafka)
  → Spark: validate + clean + normalise
  → ML: classify_event + score_credibility + generate_reasons
       + compute_duplicate_score + assign_cluster
  → weather.events (Kafka, ai.* fully populated)
  → PostgreSQL Writer
  → PostgreSQL/PostGIS (events table, geom populated)
  → GET /api/v1/events (FastAPI)
  → React Dashboard (event visible in table + map)
```

### 12.2 Checkpoints

| # | Checkpoint | How to Verify | Expected |
|---|-----------|---------------|----------|
| GP-01 | Event in `weather.raw` | kafka-ui: browse `weather.raw` topic | ≥1 message with valid Canonical Event envelope |
| GP-02 | Spark consumed event | Spark UI: Structured Streaming tab shows input rate > 0 | Micro-batch processed |
| GP-03 | ML fields populated | kafka-ui: browse `weather.events` topic | `ai.classified_category` is valid enum; `ai.credibility_score` is float 0–1 |
| GP-04 | Event in PostgreSQL | `docker compose exec postgres psql -U weather -d weatherdb -c "SELECT count(*) FROM events"` | count ≥ 1 |
| GP-05 | Geometry populated | `docker compose exec postgres psql -U weather -d weatherdb -c "SELECT ST_SRID(geom) FROM events LIMIT 1"` | 4326 |
| GP-06 | API returns event | `curl http://localhost:8000/api/v1/events` | JSON with `items` array, ≥1 item |
| GP-07 | AI fields in API | Check `items[0].classified_category` in API response | Non-null, valid enum |
| GP-08 | Dashboard shows event | Open `http://localhost:5173` | Event visible in table |
| GP-09 | Map shows marker | Open map view | Marker at correct coordinates |
| GP-10 | Detail page works | Click event | Full detail with AI breakdown visible |

### 12.3 Timing Requirement

The full golden path must complete within **~30 seconds** of the event being
produced to `weather.raw` (including Spark micro-batch interval + PG write +
API availability). Under normal demo conditions, target is **~5 seconds**
end-to-end per `01_ARCHITECTURE.md §4`.

---

## 13. Failure Tests

| # | Failure | Expected Behaviour | Recovery | Contract |
|---|---------|-------------------|----------|----------|
| F-01 | Kafka unavailable | Producer retries with backoff; consumer poll blocks | Automatic when Kafka recovers | `03_KAFKA_CONTRACT.md §10.4` |
| F-02 | PostgreSQL unavailable | Writer consumer poll blocks; events remain in Kafka | Automatic when PG recovers | `03_KAFKA_CONTRACT.md §10.6` |
| F-03 | Spark unavailable | Micro-batch in progress may be partially processed | Spark restarts; checkpoint recovery | `03_KAFKA_CONTRACT.md §10.5` |
| F-04 | Ingestion unavailable | No new events produced; existing pipeline unaffected | Restart ingestion | `01_ARCHITECTURE.md §5` |
| F-05 | API unavailable | Dashboard shows connection error; pipeline unaffected | Restart API | `04_API_CONTRACT.md §5` |
| F-06 | Frontend unavailable | Users can't access dashboard; backend unaffected | Restart frontend | `01_ARCHITECTURE.md §5` |
| F-07 | ML exception in one record | Event proceeds with null `ai.*` fields; pipeline continues | No retry; log warning | `05_AI_ML_SPEC.md §24` |
| F-08 | Malformed Kafka message | Consumer logs error; message not consumed; pipeline continues | No retry | `03_KAFKA_CONTRACT.md §11.2` |
| F-09 | Database write failure (constraint) | Writer logs error; retries on next poll; event stays in Kafka | Idempotent retry | `03_KAFKA_CONTRACT.md §10.6` |
| F-10 | Duplicate event (same `event_id`) | `ON CONFLICT DO UPDATE` overwrites; no duplicate row | Idempotent | `03_KAFKA_CONTRACT.md §10.2` |
| F-11 | Container killed during processing | `restart: unless-stopped` restarts container; resumes from checkpoint | Automatic | `07_DOCKER_DEPLOYMENT_SPEC.md §17` |
| F-12 | Kafka broker restart | Producers/consumers reconnect; resume from last committed offset | Automatic | `03_KAFKA_CONTRACT.md §10.7` |

---

## 14. Dead-Letter Tests

| # | Test | Expected | Contract |
|---|------|---------|----------|
| DL-01 | Rejected record written to filesystem | File exists at `/data/logs/dead_letter/YYYY-MM-DD/<source>_failures.jsonl` | `01_ARCHITECTURE.md §10` |
| DL-02 | Dead-letter contains original record | `original_record` field has full envelope | `01_ARCHITECTURE.md §10` |
| DL-03 | Dead-letter contains failure reasons | `failure_reasons` is non-empty array of strings | `01_ARCHITECTURE.md §10` |
| DL-04 | Dead-letter contains timestamp | `failed_at` is valid ISO 8601 UTC | `01_ARCHITECTURE.md §10` |
| DL-05 | Dead-letter contains source adapter | `source_adapter` matches the producing service | `01_ARCHITECTURE.md §10` |
| DL-06 | Records never silently discarded | After sending invalid event, dead-letter file exists AND pipeline continues | `01_ARCHITECTURE.md §10` |
| DL-07 | File rotation by day | New day → new file; old file preserved | `01_ARCHITECTURE.md §10` |
| DL-08 | File rotation by source type | Different source types → different files | `01_ARCHITECTURE.md §10` |

---

## 15. Performance Tests

### 15.1 Lightweight MVP Benchmarks

| # | Test | What to Measure | How | Contract |
|---|------|----------------|-----|----------|
| P-01 | Sustained ingestion | Events/second from ingestion → Kafka | kafka-ui message count over 5 min | `01_ARCHITECTURE.md §13` |
| P-02 | Spark processing latency | Time from Kafka consume to `weather.events` produce | Spark UI micro-batch stats | `01_ARCHITECTURE.md §4` (~5 sec target) |
| P-03 | PostgreSQL write throughput | Rows inserted per second | Monitor `pg_stat_activity` | — |
| P-04 | API response latency | `GET /events` response time | `curl` timing or k6 | — |
| P-05 | Dashboard load time | Time from page load to first render | Browser dev tools | — |

### 15.2 Synthetic Load Test (1M+ Records)

| Aspect | Detail | Contract |
|--------|--------|----------|
| Record count | 1,000,000+ | `06_IMPLEMENTATION_PLAN.md §18` |
| Format | Parquet | `06_IMPLEMENTATION_PLAN.md §18` |
| `source_type` | `"synthetic"` (always) | `01_ARCHITECTURE.md §11` |
| `source_name` | Contains `"synthetic"` | `01_ARCHITECTURE.md §11` |
| Distribution | 40% Mumbai, 35% Nagpur, 25% Nashik | `01_ARCHITECTURE.md §2` |
| Categories | Weighted random from §1.2 enum | `05_AI_ML_SPEC.md §4.1` |
| Storage | `/data/synthetic/` | `01_ARCHITECTURE.md §8` |
| Labelling | Clearly labelled; never presented as genuine | `01_ARCHITECTURE.md §11` |

### 15.3 No Fabricated Benchmarks

> **Important:** All performance numbers in this document are targets or
> measurement instructions. No specific throughput/latency numbers are claimed.
> Actual results must be measured during implementation and recorded here.

**Measured Results (to be filled during Day 5):**

| Metric | Measured Value | Date | Notes |
|--------|---------------|------|-------|
| Ingestion throughput | — | — | — |
| Spark processing latency (p50) | — | — | — |
| Spark processing latency (p99) | — | — | — |
| PG write throughput | — | — | — |
| API p50 response time | — | — | — |
| API p99 response time | — | — | — |
| Dashboard initial load | — | — | — |
| 1M synthetic generation time | — | — | — |

---

## 16. Data Quality Checks

| # | Check | Query/Method | Expected | Contract |
|---|-------|-------------|---------|----------|
| DQ-01 | Null rate: `event_id` | `SELECT count(*) FROM events WHERE event_id IS NULL` | 0 | `02_DATA_SCHEMA.md §3.1` |
| DQ-02 | Null rate: `source_type` | `SELECT count(*) FROM events WHERE source_type IS NULL` | 0 | `02_DATA_SCHEMA.md §3.1` |
| DQ-03 | Invalid coordinates | `SELECT count(*) FROM events WHERE latitude < -90 OR latitude > 90 OR longitude < -180 OR longitude > 180` | 0 | `02_DATA_SCHEMA.md §11` |
| DQ-04 | Invalid categories | `SELECT count(*) FROM events WHERE event_category NOT IN (valid enum list)` | 0 | `02_DATA_SCHEMA.md §1.2` |
| DQ-05 | Duplicate event_ids | `SELECT event_id, count(*) FROM events GROUP BY event_id HAVING count(*) > 1` | 0 rows | `02_DATA_SCHEMA.md §6.1` |
| DQ-06 | Timestamp validity | `SELECT count(*) FROM events WHERE event_timestamp > now() + interval '5 minutes'` | 0 | `02_DATA_SCHEMA.md §11` |
| DQ-07 | AI score ranges | `SELECT count(*) FROM events WHERE credibility_score < 0 OR credibility_score > 1` | 0 | `02_DATA_SCHEMA.md §3.6` |
| DQ-08 | Source distribution | `SELECT source_type, count(*) FROM events GROUP BY source_type` | All 8 source types represented (if data exists) | `02_DATA_SCHEMA.md §1.1` |
| DQ-09 | City distribution | `SELECT city, count(*) FROM events GROUP BY city` | Primarily Mumbai, Nagpur, Nashik | `01_ARCHITECTURE.md §2` |
| DQ-10 | Synthetic labelling | `SELECT count(*) FROM events WHERE source_type='synthetic' AND source_name NOT LIKE '%synthetic%'` | 0 | `01_ARCHITECTURE.md §11` |
| DQ-11 | Geometry non-null for valid coords | `SELECT count(*) FROM events WHERE latitude IS NOT NULL AND longitude IS NOT NULL AND geom IS NULL` | 0 | `02_DATA_SCHEMA.md §9` |
| DQ-12 | All verification statuses valid | `SELECT DISTINCT verification_status FROM events` | Only values from §1.4 | `02_DATA_SCHEMA.md §1.4` |

---

## 17. Security QA

| # | Check | Method | Expected | Contract |
|---|-------|--------|---------|----------|
| SEC-01 | `.env` is gitignored | `git check-ignore .env` | Returns `.env` | `01_ARCHITECTURE.md §12` |
| SEC-02 | No secrets in Git history | `git log --all -p | grep -i "password\|secret\|token"` | No real values found | `01_ARCHITECTURE.md §12` |
| SEC-03 | No secrets in Kafka messages | Inspect `weather.raw` messages | No passwords, tokens, or API keys in payload | `03_KAFKA_CONTRACT.md §13.2` |
| SEC-04 | No unnecessary PII | Inspect Canonical Event fields | No names, emails, phone numbers, IP addresses | `03_KAFKA_CONTRACT.md §13.3` |
| SEC-05 | Citizen media validation | Submit oversized/invalid file via API | Rejected with appropriate error | `04_API_CONTRACT.md §13` |
| SEC-06 | Admin auth required | `POST /verification` without JWT | 401 Unauthorized | `04_API_CONTRACT.md §3.2` |
| SEC-07 | API input validation | Send malformed JSON to any POST endpoint | 400/422 error; no crash | `04_API_CONTRACT.md §5` |
| SEC-08 | CORS restricted | Check `Access-Control-Allow-Origin` header | Only `http://localhost:5173` (not `*`) | `04_API_CONTRACT.md §20` |
| SEC-09 | SQL injection | Send `'; DROP TABLE events; --` in any text field | Treated as literal string; no SQL execution | `04_API_CONTRACT.md §22` |
| SEC-10 | Filesystem path traversal | Submit filename with `../../etc/passwd` | Rejected or sanitised | `04_API_CONTRACT.md §13` |

---

## 18. Docker QA

### 18.1 Fresh Machine Test

| # | Step | Command | Expected | Contract |
|---|------|---------|---------|----------|
| DQ-D01 | Clone | `git clone <repo>` | Source code available | `07_DOCKER_DEPLOYMENT_SPEC.md §15` |
| DQ-D02 | Configure | `cp .env.example .env` then set secrets | `.env` exists with all required vars | `07_DOCKER_DEPLOYMENT_SPEC.md §7` |
| DQ-D03 | Start | `docker compose up -d` | All 9 containers start | `07_DOCKER_DEPLOYMENT_SPEC.md §3` |
| DQ-D04 | Wait | `docker compose ps` (wait 60s) | All services healthy | `07_DOCKER_DEPLOYMENT_SPEC.md §4` |
| DQ-D05 | Kafka topics | `bash scripts/init-kafka.sh` | 7 topics created | `07_DOCKER_DEPLOYMENT_SPEC.md §9` |
| DQ-D06 | DB tables | `docker compose exec postgres psql -U weather -d weatherdb -c "\dt"` | 4 tables | `07_DOCKER_DEPLOYMENT_SPEC.md §8` |
| DQ-D07 | API health | `curl http://localhost:8000/api/v1/health` | 200 OK | `07_DOCKER_DEPLOYMENT_SPEC.md §14` |
| DQ-D08 | Smoke test | `bash scripts/smoke-test.sh` | All checks pass | `07_DOCKER_DEPLOYMENT_SPEC.md §16` |

### 18.2 Port Verification

| Port | Service | Test | Expected |
|------|---------|------|---------|
| 2181 | Zookeeper | `nc -z localhost 2181` | Connection succeeded |
| 29092 | Kafka | `kafka-topics --bootstrap-server localhost:29092 --list` | Topic list returned |
| 8080 | Kafka UI | `curl -sf http://localhost:8080` | HTML page |
| 5432 | PostgreSQL | `pg_isready -h localhost -p 5432 -U weather` | Accepting connections |
| 8081 | Spark Master UI | `curl -sf http://localhost:8081` | Spark UI page |
| 8082 | Spark Worker UI | `curl -sf http://localhost:8082` | Spark worker page |
| 8000 | API | `curl -sf http://localhost:8000/api/v1/health` | JSON health response |
| 5173 | Frontend | `curl -sf http://localhost:5173` | HTML page |

---

## 19. Test Data

### 19.1 Controlled Test Dataset

**Location:** `services/ml/tests/fixtures/` and `scripts/test_data/`

| File | Contents | Purpose |
|------|---------|---------|
| `mumbai_flood_reports.json` | 5 reports about Mumbai flooding from different sources | Corroboration + clustering test |
| `nagpur_heatwave_reports.json` | 3 heatwave reports from API + social | API-dominated classification |
| `nashik_hailstorm_reports.json` | 2 reports: citizen + simulated social | Mixed-source clustering |
| `duplicate_reports.json` | 3 near-identical reports | Duplicate detection test |
| `low_credibility_report.json` | Single report from low-trust source, no corroboration | Low credibility test |
| `invalid_events.json` | 10+ events with various defects | Validation rule tests |
| `edge_cases.json` | Empty descriptions, missing coordinates, boundary values | Edge case tests |

### 19.2 Test Data Rules

- All test data uses `source_type` values from `02_DATA_SCHEMA.md §1.1`
- Synthetic test data is clearly labelled — never presented as genuine weather reports
- Test coordinates are within Mumbai/Nagpur/Nashik bounding boxes
- Timestamps are realistic (not year 3000 or year 1900)
- Descriptions are realistic weather-event language

### 19.3 Golden Path Test Data

The golden path uses **live Open-Meteo data** — no mock required.
If Open-Meteo is unavailable during demo, fall back to pre-recorded
test event from `scripts/test_data/golden_path_event.json`.

---

## 20. Regression Checklist

Every code change must verify:

| # | Check | How | Contract |
|---|-------|-----|----------|
| R-01 | Canonical schema unchanged | Run contract tests C-01 through C-42 | `02_DATA_SCHEMA.md` |
| R-02 | Kafka contracts unchanged | Run Kafka tests K-01 through K-23 | `03_KAFKA_CONTRACT.md` |
| R-03 | API contracts unchanged | Run API tests A-01 through A-33 | `04_API_CONTRACT.md` |
| R-04 | ML output fields unchanged | Run ML tests M-01 through M-38 | `05_AI_ML_SPEC.md` |
| R-05 | Database schema unchanged | `docker compose exec postgres psql -U weather -d weatherdb -c "\dt"` | `02_DATA_SCHEMA.md §6` |
| R-06 | Docker startup still works | `docker compose down -v && docker compose up -d && bash scripts/smoke-test.sh` | `07_DOCKER_DEPLOYMENT_SPEC.md` |
| R-07 | Golden path still works | Run full golden path test (§12) | `01_ARCHITECTURE.md §14` |

---

## 21. Bug Severity

### 21.1 Severity Levels

| Level | Definition | Example | Fix Before Demo? |
|-------|-----------|---------|-----------------|
| **P0** | Demo/system completely blocked | API won't start; Kafka unreachable; DB init fails | **YES — MUST FIX** |
| **P1** | Major feature broken | Events not appearing on dashboard; ML returns wrong categories for all events | **YES — MUST FIX** |
| **P2** | Non-critical feature broken | Stats endpoint returns wrong count; map markers at wrong position | **YES if visible** |
| **P3** | Cosmetic/minor issue | UI alignment; loading spinner style; log message wording | **NO — defer** |

### 21.2 Pre-Demo Fix Requirements

| Severity | Must Fix? | Rationale |
|----------|----------|-----------|
| P0 | **Yes** | System non-functional |
| P1 | **Yes** | Major feature broken; demo fails |
| P2 | **Yes** (if visible to judges) | Observable during demo walk-through |
| P3 | No | Not visible or negligible impact |

---

## 22. Final MVP QA Checklist

### Infrastructure

- [ ] All 9 Docker containers start successfully
- [ ] All health checks pass
- [ ] Ports accessible: 2181, 29092, 8080, 5432, 8081, 8082, 8000, 5173

### Kafka

- [ ] 7 topics exist with correct configuration
- [ ] No undocumented topics
- [ ] Messages produced to `weather.raw` are valid envelopes
- [ ] Messages in `weather.events` have `ai.*` populated
- [ ] Consumer groups operational

### Spark

- [ ] Streaming job consumes from all 4 raw topics
- [ ] Validation rejects invalid events
- [ ] Dead-letter files written for rejected events
- [ ] Checkpoint directory exists and is used

### ML

- [ ] Classification returns valid enum for all 12 categories
- [ ] Confidence score in range 0.0–1.0
- [ ] Credibility score in range 0.0–1.0
- [ ] Credibility reasons are non-empty and honest
- [ ] Duplicate score in range 0.0–1.0
- [ ] Cluster ID is valid UUID or null
- [ ] ML failure does not crash pipeline

### PostgreSQL/PostGIS

- [ ] All 4 tables created
- [ ] All 11 indexes exist
- [ ] `geom` column populated for events with coordinates
- [ ] `geom` SRID is 4326
- [ ] CHECK constraints active
- [ ] `set_updated_at` trigger fires
- [ ] Seed data present (≥2 sources)

### FastAPI

- [ ] `GET /health` returns 200
- [ ] `GET /events` returns paginated results
- [ ] `GET /events/{id}` returns full detail
- [ ] `GET /events/stats` returns aggregations
- [ ] `GET /events/map` returns geospatial data
- [ ] `POST /citizen-reports` accepts valid submissions
- [ ] `POST /verification` requires JWT
- [ ] `POST /auth/login` returns token
- [ ] Swagger docs at `/docs`

### React

- [ ] Dashboard loads without errors
- [ ] KPI cards display numbers
- [ ] Map renders with markers
- [ ] Event table loads with data
- [ ] Filters update results
- [ ] Event detail shows AI breakdown
- [ ] Citizen form submits successfully
- [ ] Admin login + verify works
- [ ] Synthetic data clearly labelled

### Citizen Reports

- [ ] Full flow: form → API → Kafka → Spark → ML → PG → dashboard
- [ ] Invalid submissions rejected with correct errors
- [ ] Photo upload works

### Admin Verification

- [ ] All 4 actions work: verify, reject, suspicious, duplicate
- [ ] Verification log entries created
- [ ] `weather.verified` Kafka message produced
- [ ] Event status updates in DB

### Dead-Letter

- [ ] Invalid events written to filesystem
- [ ] Dead-letter records contain all required fields
- [ ] Pipeline continues after rejection

### Synthetic Data

- [ ] 1M+ records generated
- [ ] All records have `source_type="synthetic"`
- [ ] `source_name` contains `"synthetic"`
- [ ] Never presented as genuine in dashboard

### Security

- [ ] `.env` gitignored
- [ ] No secrets in Git
- [ ] JWT auth on admin endpoints
- [ ] CORS restricted to frontend origin
- [ ] No PII in Canonical Events

### Performance

- [ ] Golden path completes within 30 seconds
- [ ] API responds within 2 seconds
- [ ] No memory leaks during sustained operation

### Golden Path

- [ ] Open-Meteo → Kafka → Spark → ML → PG → API → Dashboard: **FULLY VISIBLE**

---

## 23. Final Cross-Contract Check

### Against `01_ARCHITECTURE.md`

| Check | Result | Notes |
|-------|--------|-------|
| All 9 services tested | ✅ PASS | Tests cover zookeeper, kafka, kafka-ui, postgres, spark-master, spark-worker, ingestion, api, frontend |
| Ports match §5 | ✅ PASS | All port tests use correct values |
| Dead-letter mechanism tested | ✅ PASS | §14 tests verify filesystem-only mechanism |
| Day-1 success criterion testable | ✅ PASS | Golden path (§12) maps to §14 checklist |
| Observability metrics testable | ✅ PASS | §15 performance tests measure pipeline metrics |

### Against `02_DATA_SCHEMA.md`

| Check | Result | Notes |
|-------|--------|-------|
| All enums validated | ✅ PASS | §2 contract tests cover §1.1–§1.4 |
| All required fields tested | ✅ PASS | §2 contract tests cover §3.1–§3.7 |
| DB schema validated | ✅ PASS | §7 PostgreSQL tests verify tables, indexes, triggers |
| Validation rules tested | ✅ PASS | §3 invalid event tests map to §11 rules |
| Geometry correctness tested | ✅ PASS | DB-03, DB-04, DB-05 verify SRID and coordinate order |

### Against `03_KAFKA_CONTRACT.md`

| Check | Result | Notes |
|-------|--------|-------|
| All 7 topics tested | ✅ PASS | §4 Kafka tests K-01 through K-08 |
| Envelope format tested | ✅ PASS | C-31 through C-37 test envelope compliance |
| Producer/consumer mapping tested | ✅ PASS | K-09 through K-16 verify correct routing |
| Consumer groups tested | ✅ PASS | K-21 through K-23 |
| Dead-letter for Kafka failures tested | ✅ PASS | K-19, K-20 test malformed messages |
| At-least-once delivery tested | ✅ PASS | F-10 tests duplicate handling; DB-11 tests idempotency |

### Against `04_API_CONTRACT.md`

| Check | Result | Notes |
|-------|--------|-------|
| All 8 endpoints tested | ✅ PASS | §8 tests A-01 through A-33 |
| All error codes tested | ✅ PASS | Invalid inputs trigger correct error codes |
| Authentication tested | ✅ PASS | A-26, A-27, A-31, A-32 test JWT flow |
| CORS tested | ✅ PASS | SEC-08 verifies restricted origins |
| Response schemas validated | ✅ PASS | C-38 through C-42 test schema compliance |

### Against `05_AI_ML_SPEC.md`

| Check | Result | Notes |
|-------|--------|-------|
| All 12 categories tested | ✅ PASS | M-01 through M-12 |
| Confidence range tested | ✅ PASS | M-16 through M-18 |
| Credibility factors tested | ✅ PASS | M-19 through M-25 |
| Duplicate detection tested | ✅ PASS | M-26 through M-30 |
| Clustering tested | ✅ PASS | M-31 through M-35 |
| Explainability honesty tested | ✅ PASS | M-25, M-37, M-38 verify no fabricated evidence |
| Failure handling tested | ✅ PASS | S-13 verifies ML failure doesn't drop events |

### Against `06_IMPLEMENTATION_PLAN.md`

| Check | Result | Notes |
|-------|--------|-------|
| Test locations match plan | ✅ PASS | Test files in `services/ml/tests/`, `services/api/tests/`, `scripts/` |
| Day-1 vertical slice testable | ✅ PASS | Golden path (§12) covers the vertical slice |
| Demo scenarios from §26 testable | ✅ PASS | ML tests M-01 through M-38 cover all 5 scenarios |
| Synthetic data generation testable | ✅ PASS | §15.2 defines the 1M+ test |

### Against `07_DOCKER_DEPLOYMENT_SPEC.md`

| Check | Result | Notes |
|-------|--------|-------|
| Docker QA tests match deployment spec | ✅ PASS | §18 tests mirror §15 startup commands |
| Volume persistence tested | ✅ PASS | DL-07, DL-08 verify filesystem persistence |
| Health checks tested | ✅ PASS | §18.2 port verification tests all health checks |
| Fresh machine test documented | ✅ PASS | §18.1 step-by-step fresh clone test |

### Summary

| Document | Contradictions | Assumptions | Unresolved Issues |
|----------|---------------|-------------|-------------------|
| `01_ARCHITECTURE.md` | 0 | 0 | 0 |
| `02_DATA_SCHEMA.md` | 0 | 0 | 0 |
| `03_KAFKA_CONTRACT.md` | 0 | 0 | 0 |
| `04_API_CONTRACT.md` | 0 | 0 | 0 |
| `05_AI_ML_SPEC.md` | 0 | 0 | 0 |
| `06_IMPLEMENTATION_PLAN.md` | 0 | 0 | 0 |
| `07_DOCKER_DEPLOYMENT_SPEC.md` | 0 | 0 | 0 |

**No contradictions found. No assumptions introduced. No unresolved issues.**

All seven contracts are internally consistent with this testing specification.

### Tests Required Before Demo

| Priority | Test Suite | Count | Blocking? |
|----------|-----------|-------|-----------|
| 1 | Golden path E2E (§12) | 10 checkpoints | **Yes** |
| 2 | Contract validation (§2) | 42 tests | **Yes** |
| 3 | ML classification (§6.1) | 15 tests | **Yes** |
| 4 | API endpoints (§8) | 33 tests | **Yes** |
| 5 | PostgreSQL (§7) | 15 tests | **Yes** |
| 6 | Kafka topics (§4) | 23 tests | **Yes** |
| 7 | Dead-letter (§14) | 8 tests | **Yes** |
| 8 | Failure recovery (§13) | 12 tests | Recommended |
| 9 | Security QA (§17) | 10 tests | **Yes** |
| 10 | Frontend smoke (§11) | 12 tests | **Yes** |
| 11 | Docker QA (§18) | 10 tests | **Yes** |
| 12 | Data quality (§16) | 12 tests | Recommended |
| 13 | Performance (§15) | 5 tests | Optional |

---

## Appendix: Test Count Summary

| Category | Mandatory | Optional | Total |
|----------|----------|---------|-------|
| Contract validation | 42 | 0 | 42 |
| Canonical event (valid/invalid) | 23 | 0 | 23 |
| Kafka | 23 | 0 | 23 |
| Spark | 17 | 0 | 17 |
| ML | 38 | 0 | 38 |
| PostgreSQL/PostGIS | 15 | 0 | 15 |
| FastAPI | 33 | 0 | 33 |
| Citizen reports | 10 | 0 | 10 |
| Admin verification | 8 | 0 | 8 |
| Frontend | 12 | 0 | 12 |
| Golden path E2E | 10 | 0 | 10 |
| Failure/recovery | 12 | 0 | 12 |
| Dead-letter | 8 | 0 | 8 |
| Performance | 1 | 7 | 8 |
| Data quality | 12 | 0 | 12 |
| Security | 10 | 0 | 10 |
| Docker QA | 10 | 0 | 10 |
| **Total** | **274** | **7** | **281** |

---

*This document is the testing and QA source of truth for the MVP.
Any change to test cases, acceptance criteria, or regression requirements
must be reflected here and cross-checked against all approved contracts.*
