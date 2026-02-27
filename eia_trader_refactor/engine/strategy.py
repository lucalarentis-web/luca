from __future__ import annotations


def label_from_score(score: float, neutral_z: float, signif_z: float, shock_z: float) -> str:
    """Map a standardized score (z) into a coarse event label."""

    a = abs(score)
    if a < neutral_z:
        return "NEUTRAL"
    if a >= shock_z:
        return "SHOCK"
    if a >= signif_z:
        return "SIGNIF"
    # between neutral and signif -> still neutral-ish (avoid overtrading)
    return "NEUTRAL"
