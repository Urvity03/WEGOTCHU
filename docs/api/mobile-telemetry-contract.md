# WEGOTCHU Mobile Telemetry Contract

Version: 0.1
Status: Draft Prototype
Issue: #1
Endpoint: POST /api/v1/telemetry

## 1. Purpose

This document defines the telemetry contract between the Android mobile client and the WEGOTCHU backend.


## 2. Data Flow

Android Mobile App
        |
        | Mobile Telemetry
        v
POST /api/v1/telemetry
        |
        v
FastAPI Backend
        |
        v
AI Risk Engine

## 3. Mobile Telemetry Payload

The mobile client sends a JSON payload containing device information, timestamp, location, movement, battery status, and network status.

Example:

{
  "version": "0.1",
  "device_id": "usr_dev_example",
  "timestamp": "2026-09-11T23:14:00.000Z",
  "location": {
    "latitude": 37.774929,
    "longitude": -122.419416,
    "altitude_meters": 16.4,
    "accuracy_meters": 4.2
  },
  "speed_mps": 1.45,
  "bearing_degrees": 182.5,
  "accelerometer": {
    "x": 0.12,
    "y": 9.78,
    "z": 1.05
  },
  "gyroscope": {
    "x": 0.01,
    "y": -0.04,
    "z": 0.02
  },
  "battery_level": 0.68,
  "network_status": "CELLULAR_4G",
  "trip_id": "trip_example_001"
}

`trip_id` is optional. Clients that omit it retain trip-independent telemetry
ingestion behavior. When supplied, it must identify an existing trip owned by
the authenticated user.

## 4. Field Definitions

Field: version
Type: string
Required: Yes
Description: Contract version

Field: device_id
Type: string
Required: Yes
Description: Mobile device identifier

Field: timestamp
Type: string
Required: Yes
Format: UTC ISO 8601
Description: Event timestamp

Field: location.latitude
Type: number
Required: Yes
Description: GPS latitude

Field: location.longitude
Type: number
Required: Yes
Description: GPS longitude

Field: location.altitude_meters
Type: number
Required: No
Description: GPS altitude

Field: location.accuracy_meters
Type: number
Required: Yes
Description: Estimated GPS accuracy

Field: speed_mps
Type: number
Required: No
Description: Current movement speed

Field: bearing_degrees
Type: number
Required: No
Description: Direction of travel

Field: accelerometer.x
Type: number
Required: Yes
Unit: m/s²
Description: X-axis acceleration

Field: accelerometer.y
Type: number
Required: Yes
Unit: m/s²
Description: Y-axis acceleration

Field: accelerometer.z
Type: number
Required: Yes
Unit: m/s²
Description: Z-axis acceleration

Field: gyroscope.x
Type: number
Required: Yes
Unit: rad/s
Description: X-axis angular velocity

Field: gyroscope.y
Type: number
Required: Yes
Unit: rad/s
Description: Y-axis angular velocity

Field: gyroscope.z
Type: number
Required: Yes
Unit: rad/s
Description: Z-axis angular velocity

Field: battery_level
Type: number
Required: Yes
Format: 0.0–1.0
Description: Battery level

Field: network_status
Type: string
Required: Yes
Description: Current network condition

Field: trip_id
Type: string
Required: No
Description: Existing trip identifier; 1-64 characters after surrounding whitespace is removed

## 5. Validation Rules

The backend should validate incoming telemetry before forwarding it to downstream components.

Location:
- Latitude must be between -90 and 90.
- Longitude must be between -180 and 180.
- Accuracy must be non-negative.

Movement:
- Speed must be non-negative when provided.
- Bearing must be between 0 and less than 360 degrees.

Battery:
- battery_level must be between 0.0 and 1.0.

Timestamp:
- Timestamp must use UTC ISO 8601 format.

Sensor Values:
- Accelerometer and gyroscope values must be numeric.
- Missing required sensor fields should cause validation failure.

## 6. Privacy Requirements

- Do not commit real user telemetry to the repository.
- Do not commit real location logs to GitHub.
- Example payloads must use synthetic/example data.
- Raw personal telemetry should not be stored unnecessarily.
- Location data handling must follow the project's privacy and data-retention policies.

## 7. Backend Responsibility

The FastAPI backend is responsible for:

1. Receiving telemetry through POST /api/v1/telemetry.
2. Validating the payload.
3. Rejecting malformed telemetry.
4. Forwarding valid telemetry to the appropriate downstream AI component.
5. Applying authentication and security controls.
6. Avoiding unnecessary persistent storage of raw personal telemetry.

### Trip Lifecycle Endpoints

Authenticated clients may initialize a trip with
`POST /api/v1/telemetry/trips/start`, providing a `trip_id` and optionally
`started_at`. Repeating a start request for the same user and trip ID is
idempotent.

Clients may finalize a trip with `POST /api/v1/telemetry/trips/complete`,
providing `trip_id` and optionally `ended_at`. Ordinary completion results in
`COMPLETED_UNVERIFIED`; an explicit crisis flag results in `ABORTED_CRISIS`,
and an anomaly flag results in `COMPLETED_ANOMALOUS`. Finalized trips cannot
be reopened or accept further telemetry. A trip ID is scoped to its
authenticated owner.

## 8. Mobile Responsibility

The Android client is responsible for:

1. Collecting GPS data during Safety Mode.
2. Collecting accelerometer data.
3. Collecting gyroscope data.
4. Attaching a valid timestamp.
5. Including device and network information.
6. Sending telemetry according to this contract.
7. Respecting battery and privacy requirements.

## 9. Performance Considerations

The project requires:

- GPS sampling at approximately 1 Hz.
- IMU sampling at approximately 50 Hz.
- Backend risk evaluation target below 250 ms.
- Active Safety Mode battery consumption below 2.5% per hour.

The backend should support efficient telemetry ingestion without unnecessary processing or storage.

## 10. Contract Compatibility

This contract is based on the existing WEGOTCHU Version 0.1 Mobile Sensor Input Payload defined in the architecture documentation.

Changes to this interface should be coordinated between the Mobile/Backend and AI/ML owners before implementation.

## 11. Status

Draft Prototype — Version 0.1

This contract should be reviewed by the AI/ML lead before backend and Android implementation begins.
