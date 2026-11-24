"""Main workbench entrypoint coordinating spectral features and non-blocking triage."""

from __future__ import annotations
from src.spectral_store import SpectralFeatureStore
from src.triage_gate import classify_disclosure

class WorkbenchSession:
    def __init__(self) -> None:
        self.store = SpectralFeatureStore()

    def inspect_and_tag(self, fid: str, nm: float, tech_choice: str) -> dict:
        peak = self.store.upsert_peak(fid, nm)
        gate = classify_disclosure('Hebbian Associative Index', tech_choice)
        return {'peak': peak, 'triage': gate}

def main() -> None:
    session = WorkbenchSession()
    session.inspect_and_tag('PK-412', 412.5, 'not_understood_prototype')

if __name__ == '__main__':
    main()
