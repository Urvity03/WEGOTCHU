# WEGOTCHU: Data Retention, Purge & Deletion Policy

## 1. Telemetry Lifecycle & Retention Schedule

WEGOTCHU enforces an automated data lifecycle ensuring that telemetry is purged as soon as its operational utility expires.

| Data Classification | Storage Location | Maximum Retention Period | Deletion Mechanism |
| :--- | :--- | :--- | :--- |
| **Raw Audio Waveforms** | Device RAM (Volatile Memory) | $\le 3.0$ seconds | Continuous FIFO buffer overwrite in memory. Never touches disk. |
| **Raw Camera Frames (P2)** | Device RAM (Volatile Memory) | $\le 1.0$ second | Memory frame overwrite after optical flow computation. |
| **Raw High-Freq IMU (50 Hz)** | Device RAM | $\le 60.0$ seconds | FIFO sliding window discard. |
| **Kinematic Feature Vectors** | Local Edge SQLite / Cache | 24 hours | Automated daily rolling vacuum and purge. |
| **Personal Baseline Statistics** | Local Edge Storage (Encrypted) | Retained during active app lifecycle | Updated continuously via online decay; deleted upon user account reset. |
| **Location Breadcrumbs** | Backend (Encrypted PostgreSQL) | 48 hours post-trip | Automated database TTL (Time-To-Live) partition purge. |
| **Emergency Incident Snapshots** | Encrypted Audit Storage | 30 days (Academic/Legal defense) | Cryptographically erased after retention window or upon user request. |

---

## 2. Cryptographic Shredding & User Erasure Rights

Users maintain the inviolable right to delete their telemetry and profile at any time:
1. **One-Tap Data Reset:** In the mobile client settings, tapping "Purge All My Data" triggers:
   * Local zero-fill overwrite of on-device baseline databases.
   * API call requesting immediate cryptographic shredding of backend user records.
2. **Account Deletion Protocol:** Upon account termination, all associated database partitions, trusted circle mappings, and incident logs are completely dropped.
