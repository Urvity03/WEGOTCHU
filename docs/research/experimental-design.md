# WEGOTCHU: Experimental Design

## 1. Initial Experiment

The first experiment investigates whether a user's current movement trajectory can be compared with their previous travel behavior to estimate how unusual the current route is.

The experiment focuses on route deviation only. It does not attempt to determine whether a person is in danger.

## 2. Trip

A trip is one continuous movement session represented by an ordered sequence of location observations belonging to the same user.

Each observation contains a location and timestamp, with additional movement and GPS-quality information where available.

Conceptually:

```text
Trip = [(location_1, time_1), (location_2, time_2), ..., (location_n, time_n)]
```

The exact rules used to segment raw GPS observations into trips will be defined after inspecting the selected dataset.

## 3. Trajectory

A trajectory is the time-ordered spatial path formed by the observations belonging to a trip.

The temporal ordering is retained because the same locations can represent different movement patterns depending on when and how they were traversed.

## 4. Historical Behavior

For each user, previously observed trips will form the initial reference set for estimating normal movement behavior.

The experiment will investigate whether comparing a current trajectory against this user-specific history provides useful information about route deviation.

## 5. Route Deviation

Route deviation represents how different a current trajectory is from routes or movement patterns previously observed for the same user.

The first system will produce a continuous:

```text
route_deviation_score in [0, 1]
```

A higher score indicates greater deviation from the available historical movement patterns.

The score should not be interpreted as a probability of danger.

For example, a completely unfamiliar route may receive a high route-deviation score while still being a normal and safe activity.

## 6. Initial Inputs

The experiment will use, where available:

* latitude
* longitude
* timestamp
* speed
* heading
* GPS accuracy
* user ID
* trip ID

Additional features may be derived during preprocessing.

## 7. Initial Experimental Progression

The first experiments will increase in complexity gradually:

1. Simple route-similarity baseline
2. Familiarity/frequency baseline
3. Classical anomaly detection
4. Personalized anomaly detection
5. Temporal modeling

Each stage will be compared with earlier approaches to determine whether the additional complexity provides a measurable improvement.

## 8. Scope Boundary

This experiment estimates movement unusualness.

It does not classify a trajectory as dangerous or safe.

The route-deviation signal will later become one input to the broader WEGOTCHU Safety Intelligence Engine.
