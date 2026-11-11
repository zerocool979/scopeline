"""CVSS scoring helpers.

Active scoring is CVSS v4.0 (FIRST specification). Historical v3.1 values are
preserved on existing findings and are never silently recalculated as v4.0.
"""
from cvss import CVSS4


class CvssError(ValueError):
    """Raised when a CVSS v4.0 vector is invalid."""


def parse_vector(vector: str) -> dict[str, str]:
    raw = (vector or "").strip()
    if not raw.startswith("CVSS:4.0/"):
        raise CvssError("Vektor kalkulator aktif harus diawali 'CVSS:4.0/'")
    try:
        parsed = CVSS4(raw)
        canonical = parsed.clean_vector()
    except Exception as exc:  # library exposes version-specific parser exceptions
        raise CvssError(f"Vektor CVSS v4.0 tidak valid: {exc}") from exc
    values: dict[str, str] = {}
    for part in canonical.split("/")[1:]:
        key, _, value = part.partition(":")
        values[key] = value
    return values


def normalize_vector(vector: str) -> str:
    raw = (vector or "").strip()
    parse_vector(raw)
    return CVSS4(raw).clean_vector()



def nomenclature(vector: str) -> str:
    values = parse_vector(vector)
    threat = values.get("E", "X") != "X"
    environmental_keys = {"CR", "IR", "AR", "MAV", "MAC", "MAT", "MPR", "MUI",
                          "MVC", "MVI", "MVA", "MSC", "MSI", "MSA"}
    environmental = any(values.get(key, "X") != "X" for key in environmental_keys)
    return "CVSS-BTE" if threat and environmental else (
        "CVSS-BT" if threat else "CVSS-BE" if environmental else "CVSS-B")


def calculate(vector: str) -> tuple[float, str]:
    """Return CVSS-B v4.0 score and qualitative rating."""
    raw = normalize_vector(vector)
    try:
        scorer = CVSS4(raw)
        score = float(scorer.scores()[0])
        rating = str(scorer.severities()[0]).lower()
    except Exception as exc:
        raise CvssError(f"Gagal menghitung CVSS v4.0: {exc}") from exc
    return score, rating
