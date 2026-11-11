import pytest

from app.cvss import CvssError, calculate, nomenclature, normalize_vector, parse_vector


@pytest.mark.parametrize("vector,score,severity", [
    ("CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:H/SI:H/SA:N", 9.9, "critical"),
    ("CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:N/VI:N/VA:N/SC:N/SI:N/SA:N", 0.0, "none"),
])
def test_cvss_v4_reference_scores(vector, score, severity):
    assert calculate(vector) == (score, severity)


def test_optional_metrics_are_preserved_and_scored():
    vector = ("CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:H/SI:H/SA:N"
              "/E:A/CR:H/IR:H/AR:H")
    assert normalize_vector(vector).endswith("/E:A/CR:H/IR:H/AR:H")
    assert calculate(vector)[0] >= 9.0


@pytest.mark.parametrize("bad", [
    "", "AV:N",
    "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
    "CVSS:4.0/AV:N/AC:L/PR:N/UI:N/VC:H/VI:H/VA:H/SC:H/SI:H/SA:H",
    "CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:X/VC:H/VI:H/VA:H/SC:H/SI:H/SA:H",
    "CVSS:4.0/AV:N/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:H/SI:H/SA:H",
])
def test_invalid_or_legacy_vectors_rejected_by_active_calculator(bad):
    with pytest.raises(CvssError):
        parse_vector(bad)


def test_vector_normalization():
    vector = "CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:N/VI:N/VA:N/SC:N/SI:N/SA:N"
    assert normalize_vector(vector) == vector


def test_cvss_nomenclature_tracks_assessed_metric_groups():
    base = "CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:N/VI:N/VA:N/SC:N/SI:N/SA:N"
    assert nomenclature(base) == "CVSS-B"
    assert nomenclature(base + "/E:A") == "CVSS-BT"
    assert nomenclature(base + "/CR:H") == "CVSS-BE"
    assert nomenclature(base + "/E:A/CR:H") == "CVSS-BTE"
