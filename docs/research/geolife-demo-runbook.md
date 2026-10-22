# GeoLife Demo Runbook

## Purpose

This runbook explains how to prepare and demonstrate the GeoLife
route-deviation pipeline for WEGOTCHU.

The demo focuses on mobility unusualness and route deviation. It does not
classify danger or provide a calibrated safety probability.

## Requirements

- Windows PowerShell
- Python 3.11
- Git
- Extracted GeoLife dataset
- WEGOTCHU repository

## Fresh Environment Setup

From a fresh repository clone, create the Python 3.11 environment:

```powershell
py -3.11 -m venv .venv311