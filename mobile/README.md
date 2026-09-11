# Module: Android Mobile Client (`mobile/`)

## Purpose & Scope
The native Android client serves as the primary user touchpoint, sensor collector, and edge inference host.

## Primary Owner
* **Lead:** Member 3 (Mobile & Backend Engineer)

## Tech Stack
* **Language:** Kotlin
* **UI Framework:** Jetpack Compose (Material 3)
* **Architecture:** Clean Architecture + MVI / MVVM
* **Sensors:** Android SensorManager (Accelerometer, Gyroscope), Google Play Services FusedLocationProviderClient
* **Background Tasks:** Android Foreground Service with persistent status notification

## Core Features (P0)
1. Seamless onboarding and privacy consent setup.
2. Safety Mode toggle with continuous foreground monitoring.
3. Inviolable Manual SOS panic button (accessible via widget or hardware volume button hold).
4. Safety Countdown Timer (with Duress PIN support).
5. Trusted contacts management and live status synchronization.
