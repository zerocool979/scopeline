import pytest

from app.cvss import CvssError, calculate, parse_vector, roundup


@pytest.mark.parametrize("vector,score,sev", [
    ("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H", 9.8, "critical"),
    ("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H", 10.0, "critical"),
    ("CVSS:3.1/AV:N/AC:L/PR:L/UI:R/S:C/C:L/I:L/A:N", 5.4, "medium"),
    ("CVSS:3.1/AV:L/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H", 7.8, "high"),
    ("CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:U/C:L/I:N/A:N", 4.3, "medium"),
    ("CVSS:3.1/AV:P/AC:H/PR:H/UI:R/S:U/C:L/I:N/A:N", 1.6, "low"),
    ("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:N", 0.0, "none"),
])
def test_known_scores(vector, score, sev):
    assert calculate(vector) == (score, sev)


@pytest.mark.parametrize("bad", [
    "", "AV:N", "CVSS:3.0/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
    "CVSS:3.1/AV:X/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
    "CVSS:3.1/AV:N/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
    "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H",
])
def test_invalid(bad):
    with pytest.raises(CvssError):
        parse_vector(bad)


def test_roundup():
    assert roundup(4.02) == 4.1
    assert roundup(4.0) == 4.0
