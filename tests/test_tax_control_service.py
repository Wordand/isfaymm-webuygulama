from services.tax_control_service import build_kdv_tax_checks


def _kdv_record(period, cumulative):
    return {
        "tur": "kdv",
        "donem": period,
        "parsed": {
            "donem": period,
            "veriler": [
                {
                    "alan": "Teslim ve Hizmetlerin Karşılığını Teşkil Eden Bedel (Kümülatif)",
                    "deger": cumulative,
                }
            ],
        },
    }


def _income_record(period, gross_sales):
    return {
        "tur": "gelir",
        "donem": period,
        "parsed": {
            "tablo": [
                {
                    "aciklama": "A. Brüt Satışlar",
                    "cari_donem": gross_sales,
                }
            ]
        },
    }


def test_december_cumulative_kdv_matches_annual_gross_sales():
    findings, _, _ = build_kdv_tax_checks(
        [_kdv_record("Aralık / 2025", "1.000.000,00")],
        [_income_record("2025", "1.000.000,00")],
        current_year=2026,
    )

    finding = next(
        item for item in findings
        if item["category"] == "KDV - gelir tablosu çapraz kontrol"
    )
    assert finding["status"] == "success"
    assert finding["period"] == "2025"
    assert finding["amount"] == 0


def test_march_cumulative_kdv_compares_with_first_temporary_gross_sales():
    findings, _, _ = build_kdv_tax_checks(
        [_kdv_record("Mart / 2026", "1.000.000,00")],
        [_income_record("2026 - 1. GEÇİCİ", "1.200.000,00")],
        current_year=2026,
    )

    finding = next(
        item for item in findings
        if item["category"] == "KDV - gelir tablosu çapraz kontrol"
    )
    assert finding["status"] == "info"
    assert finding["period"] == "2026 - 1. GEÇİCİ"
    assert finding["amount"] == 200_000
    assert "Mart" not in finding["detail"]
    assert "03/2026" in finding["detail"]
