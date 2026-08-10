import unittest

from finansal_oranlar import ORAN_DEFINITIONS, analiz_olustur, classify_ratio_level


def ratio_value(name, value):
    definition = ORAN_DEFINITIONS[name]
    return {
        "deger": value,
        "thresholds": definition.get("thresholds", {}),
        "advice": "",
    }


class FinancialRatioAnalysisTests(unittest.TestCase):
    def test_high_debt_ratios_are_risky(self):
        self.assertEqual(
            classify_ratio_level(
                "Yabancı Kaynak Oranı",
                0.80,
                ORAN_DEFINITIONS["Yabancı Kaynak Oranı"]["thresholds"],
            ),
            "risky",
        )
        self.assertEqual(
            classify_ratio_level(
                "Borç/Özsermaye Oranı",
                3.95,
                ORAN_DEFINITIONS["Borç/Özsermaye Oranı"]["thresholds"],
            ),
            "risky",
        )

    def test_low_long_term_debt_and_stock_dependency_are_safe(self):
        self.assertEqual(
            classify_ratio_level(
                "Uzun Vadeli Yabancı Kaynak Oranı",
                0.08,
                ORAN_DEFINITIONS["Uzun Vadeli Yabancı Kaynak Oranı"]["thresholds"],
            ),
            "safe",
        )
        self.assertEqual(
            classify_ratio_level(
                "Stok Bağımlılık Oranı",
                0.24,
                ORAN_DEFINITIONS["Stok Bağımlılık Oranı"]["thresholds"],
            ),
            "safe",
        )

    def test_debt_increase_is_colored_as_negative(self):
        reports = {
            "2023": {"Borç/Özsermaye Oranı": ratio_value("Borç/Özsermaye Oranı", 0.74)},
            "2024": {"Borç/Özsermaye Oranı": ratio_value("Borç/Özsermaye Oranı", 1.88)},
            "2025": {"Borç/Özsermaye Oranı": ratio_value("Borç/Özsermaye Oranı", 3.95)},
        }

        result = analiz_olustur(reports)["oran_analizleri"]["Borç/Özsermaye Oranı"]

        self.assertEqual(result["trend"], "Güçlü artış")
        self.assertEqual(result["trend_tone"], "negative")
        self.assertEqual(result["seviye"], "risky")
        self.assertIn("mevcut seviye: riskli", result["sonucu"].lower())

    def test_volatile_margin_is_not_presented_as_simple_growth(self):
        reports = {
            "2023": {"Net Kar Marjı (Satışların Karlılığı)": ratio_value("Net Kar Marjı (Satışların Karlılığı)", 6.17)},
            "2024": {"Net Kar Marjı (Satışların Karlılığı)": ratio_value("Net Kar Marjı (Satışların Karlılığı)", 11.26)},
            "2025": {"Net Kar Marjı (Satışların Karlılığı)": ratio_value("Net Kar Marjı (Satışların Karlılığı)", 4.83)},
            "2026 - 1. GEÇİCİ": {"Net Kar Marjı (Satışların Karlılığı)": ratio_value("Net Kar Marjı (Satışların Karlılığı)", 6.41)},
        }

        result = analiz_olustur(reports)["oran_analizleri"]["Net Kar Marjı (Satışların Karlılığı)"]

        self.assertEqual(result["trend"], "Dalgalı seyir")
        self.assertEqual(result["trend_tone"], "neutral")
        self.assertNotIn("dönem farkı gözetilerek", result["sonucu"])
        self.assertTrue(analiz_olustur(reports)["gecici_donem_var"])

    def test_ratios_follow_definition_order(self):
        reports = {
            "2025": {
                "Net Kar Marjı (Satışların Karlılığı)": ratio_value("Net Kar Marjı (Satışların Karlılığı)", 4.83),
                "Cari Oran": ratio_value("Cari Oran", 1.22),
                "Borç/Özsermaye Oranı": ratio_value("Borç/Özsermaye Oranı", 3.95),
                "Stok Devir Hızı": ratio_value("Stok Devir Hızı", 17.35),
            }
        }

        names = list(analiz_olustur(reports)["oran_analizleri"])

        self.assertEqual(
            names,
            ["Cari Oran", "Borç/Özsermaye Oranı", "Stok Devir Hızı", "Net Kar Marjı (Satışların Karlılığı)"],
        )


if __name__ == "__main__":
    unittest.main()
