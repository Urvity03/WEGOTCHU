# WEGOTCHU: Component Interaction Patterns

## 1. System Interaction Scenarios

This document details runtime sequence flows, error recovery, and graceful degradation strategies across WEGOTCHU's edge mobile client, backend infrastructure, and external communication gateways.

---

## 2. Interaction Flow: Elevated Risk & Discreet Check-in

```mermaid
sequenceDiagram
    autonumber
    actor User as User
    participant Android as Android Mobile App
    participant SensorPipe as Sensor Pipeline
    participant EdgeAI as Local Edge AI
    participant Backend as FastAPI Backend
    participant Policy as Policy Engine

    User->>Android: Activates "Safety Mode"
    Android->>SensorPipe: Start Background Sensor Sampling
    SensorPipe->>EdgeAI: In-memory Window Buffers (IMU, GPS)
    
    Note over EdgeAI: Detects route deviation + rapid pacing
    EdgeAI->>Backend: Post Feature Telemetry
    Backend->>Policy: Evaluate Anomaly Vector
    
    Policy->>Policy: State changes from NORMAL to ELEVATED
    Policy->>Android: Command: TRIGGER_DISCREET_CHECKIN (timeout=30s)
    
    Android->>User: Gentle Haptic Pattern (Screen remains subtle)
    
    alt User Confirms "I am Safe"
        User->>Android: Taps "I'm Safe" (or enters silent PIN)
        Android->>Policy: Check-in Acknowledged (SAFE)
        Policy->>Backend: Log User Feedback
        Backend->>EdgeAI: Update Local Baseline Calibration
        Android->>User: Returns to Passive Monitoring
    else User Does Not Respond within 30s
        Android->>Policy: Timeout Expired
        Policy->>Policy: State Escalates from ELEVATED to HIGH
    end
```

---

## 3. Interaction Flow: High Risk Escalation & Trusted Circle Alert

```mermaid
sequenceDiagram
    autonumber
    participant Policy as Policy Engine
    participant Android as Android Mobile App
    participant GenAI as GenAI Gateway
    participant Dispatch as Notification Dispatcher
    actor Contacts as Trusted Contacts

    Note over Policy: State Escalates to HIGH
    Policy->>Android: Initiate Pre-Alert Siren Warning (10s cancel window)
    
    opt User Cancels Alert
        Android->>Policy: Cancelled via Biometric / PIN
        Policy->>Policy: De-escalate to NORMAL
    end

    Note over Policy: Cancel window expires without intervention
    Policy->>Policy: Transition to EMERGENCY
    
    Policy->>GenAI: Request Synthesized Briefing (Structured Payload)
    GenAI->>GenAI: Enforce Safety System Prompt & Format Validation
    GenAI-->>Policy: Validated Alert Text & Summaries
    
    Policy->>Dispatch: Send Emergency Dispatch Request
    Dispatch->>Contacts: Broadcast SMS with Live Location URL
    Dispatch->>Contacts: Push Notification to Trusted Circle
    Android->>Android: Enable Continuous Emergency GPS Beacon
```

---

## 4. Interaction Flow: Inviolable Manual SOS Bypass

```mermaid
sequenceDiagram
    autonumber
    actor User as User
    participant Android as Android Mobile App
    participant Policy as Policy Engine
    participant Dispatch as Notification Dispatcher
    actor Contacts as Trusted Contacts

    User->>Android: Presses Hardware / Screen Panic SOS (Hold 1.5s)
    
    Note over Android: Bypasses ALL ML inference layers immediately
    Android->>Policy: IMMEDIATE_MANUAL_SOS_TRIGGER
    Policy->>Policy: Instant State Transition: EMERGENCY (< 50ms)
    
    par Parallel Dispatch
        Policy->>Android: Trigger Emergency Beacon & Camera Snapshot
        Policy->>Dispatch: Trigger Emergency Broadcast (Template fallback if offline)
        Dispatch->>Contacts: Deliver Emergency Alert & Coordinates
    end
```

---

## 5. Offline Degradation & Fault Tolerance Strategies

| Failure Mode | Detection Indicator | Graceful Degradation Strategy |
| :--- | :--- | :--- |
| **Complete Network Loss (Offline)** | HTTP timeout / Socket disconnect | Android client runs standalone ONNX/LiteRT model on-device; if state reaches `HIGH`/`EMERGENCY`, triggers direct SMS via cellular carrier (no internet required). |
| **Degraded GPS Accuracy (> 50m)** | GPS `accuracy_meters` field | Fusion engine lowers GPS geospatial weighting and increases IMU cadence and pedometer dead-reckoning reliance. |
| **Low Battery (< 15%)** | Android BatteryManager | Sensor polling rate dynamically throttles (GPS drops from 1Hz to 0.1Hz; audio analysis interval increases from 1s to 5s). |
| **GenAI Service Failure / Timeout** | API timeout (> 5s) or HTTP 5xx | Policy Engine immediately falls back to deterministic rule-based template strings (`"EMERGENCY: User requires assistance at [Lat, Lon]."`). Emergency alerts are **never** blocked by LLM downtime. |
