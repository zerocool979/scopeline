"""Kalkulator CVSS v3.1 (skor dasar) sesuai spesifikasi FIRST."""
import math

METRICS = {
    "AV": {"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.2},
    "AC": {"L": 0.77, "H": 0.44},
    "PR": {"N": 0.85, "L": 0.62, "H": 0.27},
    "UI": {"N": 0.85, "R": 0.62},
    "S": {"U": None, "C": None},
    "C": {"H": 0.56, "L": 0.22, "N": 0.0},
    "I": {"H": 0.56, "L": 0.22, "N": 0.0},
    "A": {"H": 0.56, "L": 0.22, "N": 0.0},
}
PR_CHANGED = {"N": 0.85, "L": 0.68, "H": 0.5}


class CvssError(ValueError):
    pass


def parse_vector(vector: str) -> dict:
    parts = (vector or "").strip().split("/")
    if not parts or parts[0] != "CVSS:3.1":
        raise CvssError("Vektor harus diawali 'CVSS:3.1'")
    values: dict = {}
    for part in parts[1:]:
        key, sep, val = part.partition(":")
        if not sep or key in values or key not in METRICS or val not in METRICS[key]:
            raise CvssError(f"Metrik tidak valid: '{part}'")
        values[key] = val
    missing = [k for k in METRICS if k not in values]
    if missing:
        raise CvssError("Metrik belum lengkap: " + ", ".join(missing))
    return values


def roundup(x: float) -> float:
    i = round(x * 100000)
    if i % 10000 == 0:
        return i / 100000.0
    return (math.floor(i / 10000) + 1) / 10.0


def severity_of(score: float) -> str:
    if score == 0:
        return "none"
    if score < 4.0:
        return "low"
    if score < 7.0:
        return "medium"
    if score < 9.0:
        return "high"
    return "critical"


def calculate(vector: str) -> tuple[float, str]:
    m = parse_vector(vector)
    changed = m["S"] == "C"
    iss = 1 - (1 - METRICS["C"][m["C"]]) * (1 - METRICS["I"][m["I"]]) * (1 - METRICS["A"][m["A"]])
    if changed:
        impact = 7.52 * (iss - 0.029) - 3.25 * (iss - 0.02) ** 15
    else:
        impact = 6.42 * iss
    pr = (PR_CHANGED if changed else METRICS["PR"])[m["PR"]]
    expl = 8.22 * METRICS["AV"][m["AV"]] * METRICS["AC"][m["AC"]] * pr * METRICS["UI"][m["UI"]]
    if impact <= 0:
        score = 0.0
    elif changed:
        score = roundup(min(1.08 * (impact + expl), 10))
    else:
        score = roundup(min(impact + expl, 10))
    return score, severity_of(score)
