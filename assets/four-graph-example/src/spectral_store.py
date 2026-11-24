"""Persistent addressable store for spectral peak features and annotations."""

from __future__ import annotations

class SpectralFeatureStore:
    def __init__(self) -> None:
        self._features: dict[str, dict] = {}

    def upsert_peak(self, feature_id: str, wavelength_nm: float, note: str = '') -> dict:
        rec = {'id': feature_id, 'wavelength_nm': wavelength_nm, 'note': note}
        self._features[feature_id] = rec
        return rec

    def get_peak(self, feature_id: str) -> dict | None:
        return self._features.get(feature_id)
