# Module: Personal Behavioral Baseline (`ai/personalization/`)

## Purpose & Scope
This module learns individualized behavioral norms (e.g., commute corridors, baseline walking speed, routine active hours) to suppress false alarms. A behavior that is anomalous for the general population (e.g., walking at midnight) may be normal for a specific user.

## Primary Owner
* **Lead:** Project Lead (Member 1)
* **Collaborator:** Member 2 (Data Science Lead)

## Inputs & Outputs
* **Input:** Historical user mobility features, time-of-day, day-of-week, route corridor traces.
* **Output:** User-conditioned distance metric / likelihood penalty ($z$-score or Mahalanobis distance).

## Key Approaches
* Online Gaussian Mixture Models (GMM)
* Incremental Mahalanobis Distance estimators
* Spatial corridor boundary representations (geospatial envelope)

## Privacy Constraint
All personal baseline statistics are computed and updated on-device. Raw personal routines are never harvested into a central database.
