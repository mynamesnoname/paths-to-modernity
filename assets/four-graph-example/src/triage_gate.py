"""Three-way technical disclosure gate and reversible prototype scope checker."""

from __future__ import annotations

ALLOWED_TRIAGE = {'understood_agreed', 'not_understood_prototype', 'disagreed_counterproposal'}

def classify_disclosure(term: str, choice: str) -> dict:
    if choice not in ALLOWED_TRIAGE:
        raise ValueError(f'Invalid choice: {choice}')
    return {'term': term, 'choice': choice, 'bookmark': choice == 'not_understood_prototype'}
