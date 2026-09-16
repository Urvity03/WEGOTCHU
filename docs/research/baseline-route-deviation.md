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

## 3. Point-to-Point Distance

Geographic distance between two GPS observations will be calculated using the Haversine distance.

The distance is expressed in metres.

This is preferred over directly comparing latitude and longitude values because GPS coordinates represent positions on the Earth's surface.

## 4. Trajectory Similarity

Two trajectories will initially be compared using Dynamic Time Warping (DTW).

DTW allows trajectories with different numbers of observations or different sampling intervals to be aligned.

The resulting DTW distance represents the spatial difference between the two trajectories under the chosen alignment.

## 5. Personalized Reference Set

For a current trajectory belonging to user `u`, the reference set will consist of previously observed trajectories from the same user.

The current trajectory will not be compared against a pooled population as the primary baseline.

The historical reference set must precede the current trajectory in time to avoid using future information.

## 6. Initial Deviation Measure

For a current trajectory, DTW distance will be calculated against eligible historical trajectories belonging to the same user.

The baseline will initially use the minimum DTW distance to any eligible historical trajectory as the measure of route deviation.

A higher distance indicates that the current trajectory is less similar to the user's historical movement patterns.

## 7. Route Deviation Score

The raw trajectory distance will later be transformed into a normalized:

```text
route_deviation_score in [0, 1]
```

The normalization method will be determined from the distribution of distances in the training/reference data rather than by selecting an arbitrary fixed threshold.

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
