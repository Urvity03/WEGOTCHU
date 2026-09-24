# WEGOTCHU: Route Deviation Baseline v0.1

## 1. Objective

Establish a simple and interpretable baseline for estimating how different a current user trajectory is from their previously observed travel behavior.

This baseline is intended to provide a reference point for later personalized and temporal ML models.

## 2. Trajectory Representation

A trajectory is represented as an ordered sequence of GPS observations:

```text
T = [p_1, p_2, ..., p_n]
```

Each observation contains:

```text
p_i = (latitude_i, longitude_i, timestamp_i)
```

The observations are ordered chronologically.

For the v0.1 baseline, irregular timestamp gaps between consecutive observations are preserved as-is without synthetic temporal imputation. Unusually large gaps (such as extended recording cutoffs or stationary periods) are handled during trip segmentation by splitting trajectories at significant recording interruptions rather than warping across disjoint travel sessions.

## 3. Point-to-Point Distance

Geographic distance between two GPS observations will be calculated using the Haversine distance.

The distance is expressed in metres.

This is preferred over directly comparing latitude and longitude values because GPS coordinates represent positions on the Earth's surface.

## 4. Trajectory Similarity

Two trajectories will initially be compared using Dynamic Time Warping (DTW).

DTW computes the optimal alignment between two ordered sequences of GPS observations using pairwise Haversine distance (in metres) as the local cost measure between point $p_i$ and point $p_j$:

```text
cost(p_i, p_j) = haversine(latitude_i, longitude_i, latitude_j, longitude_j)
```

The v0.1 baseline does not require or apply trajectory resampling (such as spatial or temporal downsampling/interpolation) prior to DTW comparison. DTW naturally accommodates sequences of different lengths and varying observation densities without introducing heuristic resampling artifacts.

The resulting DTW distance represents the cumulative spatial difference between the two trajectories under the optimal alignment.

## 5. Personalized Reference Set

For a current trajectory belonging to user `u`, the reference set will consist of previously observed trajectories from the same user.

The current trajectory will not be compared against a pooled population as the primary baseline.

The historical reference set must precede the current trajectory in time to avoid using future information.

### Minimum History Requirement
The minimum number of historical trajectories ($k_{\text{min}}$) required to establish a valid personalized reference set is treated as an experimental hyperparameter in the v0.1 baseline (with initial empirical evaluations targeting $k_{\text{min}} \ge 5$). The exact threshold will be evaluated during dataset exploration to ensure sufficient corridor coverage without excluding viable users.

### Cold-Start Behavior
For a user with fewer than $k_{\text{min}}$ historical trajectories in their reference set, the baseline does not compute an uncalibrated score or fall back to an unverified population model. Instead, the baseline reports an explicit `INSUFFICIENT_HISTORY` (cold-start) status. This ensures that the system avoids producing unreliable deviation estimates before an individual behavioral baseline has been established. This behavior is strictly informational and does not trigger safety-risk classification.

## 6. Initial Deviation Measure

For a current trajectory, DTW distance will be calculated against eligible historical trajectories belonging to the same user.

The baseline will initially use the minimum DTW distance to any eligible historical trajectory as the measure of route deviation.

A higher distance indicates that the current trajectory is less similar to the user's historical movement patterns.

## 7. Route Deviation Score

The raw trajectory distance will later be transformed into a normalized:

```text
route_deviation_score in [0, 1]
```

The normalization method (such as empirical cumulative distribution scaling or robust percentile scaling) will be determined and fitted strictly on the distribution of distances in the training/reference data rather than by selecting an arbitrary fixed threshold.

### Anti-Data-Leakage Rule
Parameters fitted for score normalization (e.g., scaling bounds, minimum/maximum values, or empirical quantiles) must be computed exclusively from the historical reference/training trajectories. Once fitted, these parameters are applied unchanged to validation and test trajectories. Under no circumstances may validation or test trajectory distances influence the fitted normalization parameters or reference distributions.

The score represents movement unusualness and is not a probability of danger.

## 8. Data Limitations

The GeoLife dataset does not provide ground-truth safety or danger labels.

Therefore, the baseline must not be evaluated as a direct danger classifier.

Evaluation will use historical trajectory holdout strategies and, where appropriate, controlled or synthetic route deviations with clearly documented construction procedures.

## 9. Initial Scope

The first baseline uses:

* latitude
* longitude
* timestamp
* user identity
* trajectory identity

Speed and bearing may be derived later from consecutive observations.

Altitude, GPS accuracy, and other modalities are outside the initial DTW baseline unless subsequent experiments show that they provide useful information.

## 10. Research Progression

The baseline provides the reference point for later experiments:

```text
DTW route-similarity baseline
            ↓
classical anomaly detection
            ↓
personalized behavioral model
            ↓
temporal model
            ↓
multimodal risk estimation
```

The purpose of the baseline is not to be the final WEGOTCHU model, but to establish a reproducible reference against which more complex approaches can be evaluated.
