from app.services.scam_check import scam_check


def test_real_style_notice_is_low(sample_text):
    assert scam_check(sample_text)["level"] == "low"


def test_obvious_scam_is_high():
    text = ("Army recruitment 2026! 100% selection without exam. Pay Rs 1500 registration fee to our PhonePe number. "
            "Hurry, limited seats. Contact jobs.army@gmail.com. Apply at www.armyjobs-india.com")
    r = scam_check(text)
    assert r["level"] == "high" and len(r["reasons"]) >= 3
