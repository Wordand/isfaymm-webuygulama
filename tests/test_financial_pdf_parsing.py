import unittest

import pandas as pd

from routes.data_routes import is_gecici_vergi_pdf, process_parsed_parts
from routes.report_routes import _calculate_available_financial_ratios, _required_report_types_for_category
from services.pdf_service import (
    canonicalize_bilanco_rows,
    canonicalize_gelir_rows,
    parse_bilanco_from_pdf,
    parse_gelir_from_pdf,
    parse_numeric_columns,
    parse_table_block,
)
from services.utils import tlformat


class FinancialPdfParsingTests(unittest.TestCase):
    def test_financial_analysis_category_table_requirements(self):
        self.assertEqual(_required_report_types_for_category("karlilik"), {"gelir"})
        self.assertEqual(_required_report_types_for_category("likidite"), {"bilanco"})
        self.assertEqual(_required_report_types_for_category("yapi"), {"bilanco"})
        self.assertEqual(_required_report_types_for_category("varlik"), {"bilanco", "gelir"})

    def test_2025_two_column_row_ignores_display_number(self):
        description, previous, current, inflation = parse_numeric_columns(
            ". 1. Kasa 0,00 32.584,25",
            expected_columns=2,
        )

        self.assertEqual(description, "Kasa")
        self.assertEqual(previous, 0.0)
        self.assertEqual(current, 32584.25)
        self.assertIsNone(inflation)

    def test_2023_three_column_row_keeps_inflation_value(self):
        description, previous, current, inflation = parse_numeric_columns(
            ". 1. Kasa 461.000,61 276.891,54 276.891,54",
            expected_columns=3,
        )

        self.assertEqual(description, "Kasa")
        self.assertEqual(previous, 461000.61)
        self.assertEqual(current, 276891.54)
        self.assertEqual(inflation, 276891.54)

    def test_balance_parser_uses_header_column_count(self):
        text = """
AKTİF
Açıklama Önceki Dönem Cari Dönem
(2024) (2025)
I. Dönen Varlıklar 0,00 387.440.634,65
. A. Hazır Değerler 0,00 160.787.489,62
. 1. Kasa 0,00 32.584,25
AKTİF TOPLAMI 0,00 442.946.605,73
"""

        frame, has_inflation = parse_table_block(text, "AKTİF", debug=False)
        kasa = frame.loc[frame["Kod"] == "100"].iloc[0]

        self.assertFalse(has_inflation)
        self.assertEqual(kasa["Önceki Dönem"], 0.0)
        self.assertEqual(kasa["Cari Dönem"], 32584.25)
        self.assertNotIn("Cari Dönem (Enflasyonlu)", frame.columns)

    def test_2023_balance_parser_detects_real_inflation_column(self):
        text = """
AKTİF
Enflasyon Düzeltmesi Sonrası
Açıklama Önceki Dönem Cari Dönem Cari Dönem
(2022) (2023) (2023)
I. Dönen Varlıklar 45.585.616,10 73.634.661,36 75.938.235,38
. A. Hazır Değerler 12.144.394,45 12.901.277,97 12.901.277,97
. 1. Kasa 461.000,61 276.891,54 276.891,54
AKTİF TOPLAMI 51.873.824,43 79.981.694,61 88.304.093,40
"""

        frame, has_inflation = parse_table_block(text, "AKTİF", debug=False)
        kasa = frame.loc[frame["Kod"] == "100"].iloc[0]

        self.assertTrue(has_inflation)
        self.assertEqual(kasa["Önceki Dönem"], 461000.61)
        self.assertEqual(kasa["Cari Dönem"], 276891.54)
        self.assertEqual(kasa["Cari Dönem (Enflasyonlu)"], 276891.54)

    def test_duplicate_account_names_follow_balance_context(self):
        text = """
PASİF
Açıklama Önceki Dönem Cari Dönem
(2024) (2025)
III. Kısa Vadeli Yabancı Kaynaklar 0,00 318.858.622,21
. A. Mali Borçlar 0,00 51.561.367,44
. 1. Banka Kredileri 0,00 46.710.496,48
IV. Uzun Vadeli Yabancı Kaynaklar 0,00 34.561.279,49
. A. Mali Borçlar 0,00 34.561.279,49
. 1. Banka Kredileri 0,00 34.561.279,49
PASİF TOPLAMI 0,00 442.946.605,73
"""

        frame, _ = parse_table_block(text, "PASİF", debug=False)
        bank_rows = frame.loc[frame["Açıklama"] == "Banka Kredileri"]

        self.assertEqual(bank_rows["Kod"].tolist(), ["300", "400"])

    def test_negative_balance_accounts_are_stored_negative(self):
        text = """
AKTİF
Açıklama Önceki Dönem Cari Dönem
(2024) (2025)
I. Dönen Varlıklar 0,00 387.440.634,65
. A. Hazır Değerler 0,00 160.787.489,62
. 4. Verilen Çekler ve Ödeme Emirleri (-) 0,00 2.369.000,00
AKTİF TOPLAMI 0,00 442.946.605,73
"""

        frame, _ = parse_table_block(text, "AKTİF", debug=False)
        row = frame.loc[frame["Kod"] == "103"].iloc[0]

        self.assertEqual(row["Cari Dönem"], -2369000.0)

    def test_exact_account_name_wins_before_partial_match(self):
        text = """
AKTİF
Açıklama Önceki Dönem Cari Dönem
(2022) (2023)
I. Dönen Varlıklar 45.585.616,10 73.634.661,36
. E. Stoklar 2.978.126,90 13.964.115,82
. 3. Mamuller 0,00 2.000.000,00
AKTİF TOPLAMI 51.873.824,43 79.981.694,61
"""

        frame, _ = parse_table_block(text, "AKTİF", debug=False)
        row = frame.loc[frame["Açıklama"] == "Mamuller"].iloc[0]

        self.assertEqual(row["Kod"], "152")

    def test_repeated_passive_header_does_not_drop_first_page(self):
        text = """
KURUMLAR VERGİSİ BEYANNAMESİ
Yıl: 2023 Ay: Aralık
AKTİF
Enflasyon Düzeltmesi Sonrası
Açıklama Önceki Dönem Cari Dönem Cari Dönem
(2022) (2023) (2023)
I. Dönen Varlıklar 45.585.616,10 73.634.661,36 75.938.235,38
AKTİF TOPLAMI 51.873.824,43 79.981.694,61 88.304.093,40
PASİF
Enflasyon Düzeltmesi Sonrası
Açıklama Önceki Dönem Cari Dönem Cari Dönem
(2022) (2023) (2023)
III. Kısa Vadeli Yabancı Kaynaklar 30.716.781,16 34.132.780,22 34.270.728,33
. A. Mali Borçlar 376.486,76 4.291.781,16 4.291.781,16
. 1. Banka Kredileri 149.457,38 3.788.154,93 3.788.154,93
--- Sayfa 5 ---
PASİF
Enflasyon Düzeltmesi Sonrası
Açıklama Önceki Dönem Cari Dönem Cari Dönem
(2022) (2023) (2023)
. F. Ödenecek Vergi ve Diğer Yükümlülükler 1.894.299,51 849.501,96 849.501,96
. 3. Vadesi Geçmiş Ertelenmiş veya 63.300,39 309.240,01 309.240,01
V. Öz Kaynaklar 21.133.371,82 45.848.914,39 54.033.365,07
PASİF TOPLAMI 51.873.824,43 79.981.694,61 88.304.093,40
GELİR TABLOSU
"""

        result = parse_bilanco_from_pdf("unused.pdf", text_content=text)
        codes = [row["Kod"] for row in result["pasif"]]

        self.assertIn("300", codes)
        self.assertIn("368", codes)
        self.assertEqual(result["pasif"][0]["Açıklama"], "III. Kısa Vadeli Yabancı Kaynaklar")

    def test_truncated_balance_labels_are_expanded_from_mapping(self):
        rows = [
            {"Kod": "", "Açıklama": "III. Kısa Vadeli Yabancı Kaynaklar"},
            {"Kod": "", "Açıklama": "F.Ödenecek Vergi ve Diğer"},
            {"Kod": "368", "Açıklama": "Vadesi Geçmiş Ertelenmiş veya"},
            {"Kod": "", "Açıklama": "G. Borç ve Gider Karşılıkları"},
            {"Kod": "370", "Açıklama": "Dönem Karı Vergi ve Diğer Yasal"},
            {"Kod": "371", "Açıklama": "Dönem Karının Peşin Ödenen"},
        ]

        normalized = canonicalize_bilanco_rows(rows, "PASİF")

        self.assertEqual(
            normalized[1]["Açıklama"],
            "F. Ödenecek Vergi ve Diğer Yükümlülükler",
        )
        self.assertEqual(
            normalized[2]["Açıklama"],
            "Vadesi Geçmiş, Ertelenmiş veya Taksitlendirilmiş Vergi ve Diğer Yükümlülükler",
        )
        self.assertEqual(
            normalized[4]["Açıklama"],
            "Dönem Karı Vergi ve Diğer Yasal Yükümlülük Karşılıkları",
        )
        self.assertEqual(
            normalized[5]["Açıklama"],
            "Dönem Karının Peşin Ödenen Vergi ve Diğer Yükümlülükleri (-)",
        )

    def test_current_and_noncurrent_prepaid_expense_group_labels(self):
        rows = [
            {"Kod": "", "Açıklama": "I. Dönen Varlıklar"},
            {"Kod": "", "Açıklama": "G. Gelecek Aylara Ait Giderler"},
            {"Kod": "180", "Açıklama": "Gelecek Aylara Ait Giderler"},
            {"Kod": "", "Açıklama": "II. Duran Varlıklar"},
            {"Kod": "", "Açıklama": "G. Gelecek Yıllara Ait Giderler"},
            {"Kod": "280", "Açıklama": "Gelecek Yıllara Ait Giderler"},
        ]

        normalized = canonicalize_bilanco_rows(rows, "AKTİF")

        self.assertEqual(
            normalized[1]["Açıklama"],
            "G. Gelecek Aylara Ait Giderler ve Gelir Tahakkukları",
        )
        self.assertEqual(normalized[2]["Açıklama"], "Gelecek Aylara Ait Giderler")
        self.assertEqual(
            normalized[4]["Açıklama"],
            "G. Gelecek Yıllara Ait Giderler ve Gelir Tahakkukları",
        )
        self.assertEqual(normalized[5]["Açıklama"], "Gelecek Yıllara Ait Giderler")

    def test_negative_zero_is_displayed_as_zero(self):
        self.assertEqual(tlformat(-0.0), "0,00")

    def test_income_parser_ignores_display_number(self):
        text = """
KURUMLAR VERGİSİ BEYANNAMESİ
Yıl: 2025 Ay: Aralık
GELİR TABLOSU
Açıklama Önceki Dönem Cari Dönem
(2024) (2025)
A. Brüt Satışlar 0,00 571.390.302,52
. 1. Yurtiçi Satışlar 0,00 569.654.929,06
Dönem Net Karı veya Zararı 0,00 26.640.295,95
"""

        result = parse_gelir_from_pdf("unused.pdf", text_content=text)
        row = next(item for item in result["tablo"] if item["kod"] == "600")

        self.assertEqual(row["onceki_donem"], 0.0)
        self.assertEqual(row["cari_donem"], 569654929.06)
        self.assertIsNone(row["cari_donem_enflasyonlu"])

    def test_single_column_income_row_ignores_display_number(self):
        description, previous, current, inflation = parse_numeric_columns(
            ". 1. Yurtiçi Satışlar 257.114.582,09",
            expected_columns=1,
        )

        self.assertEqual(description, "Yurtiçi Satışlar")
        self.assertIsNone(previous)
        self.assertEqual(current, 257114582.09)
        self.assertIsNone(inflation)

    def test_gecici_vergi_income_table_uses_current_column_only(self):
        text = """
GEÇİCİ VERGİ BEYANNAMESİ
( Kurumlar Vergisi Mükellefleri İçin )
DÖNEM TİPİ Yılı 2026
Geçici Vergi Dönemi (Normal Dönem) Dönem 1. Dönem
Vergi Kimlik Numarası 0080896549
Soyadı (Unvanı) TEST ŞİRKETİ
EKLER
TEK DÜZEN HESAP PLANINA UYGUN GELİR TABLOSU ( TL )
Açıklama Cari Dönem
(2026)
A. Brüt Satışlar 257.114.582,09
. 1. Yurtiçi Satışlar 257.114.582,09
B. Satış İndirimleri (-) 3.683.731,92
. 1. Satıştan İadeler (-) 3.683.731,92
C.Net Satışlar 253.430.850,17
Dönem Net Karı veya Zararı 16.240.336,56
"""

        result = parse_gelir_from_pdf("unused.pdf", text_content=text)
        yurtiçi = next(item for item in result["tablo"] if item["kod"] == "600")
        iade = next(item for item in result["tablo"] if item["kod"] == "610")

        self.assertEqual(result["donem"], "2026 - 1. GEÇİCİ")
        self.assertIsNone(yurtiçi["onceki_donem"])
        self.assertEqual(yurtiçi["cari_donem"], 257114582.09)
        self.assertEqual(iade["cari_donem"], -3683731.92)

    def test_gecici_vergi_period_is_not_collapsed_into_annual_year(self):
        parsed = {
            "donem": "2026 - 1. GEÇİCİ",
            "has_inflation": False,
            "tablo": [
                {
                    "kod": "600",
                    "aciklama": "Yurtiçi Satışlar",
                    "onceki_donem": None,
                    "cari_donem": 257114582.09,
                    "cari_donem_enflasyonlu": None,
                }
            ],
        }

        records = process_parsed_parts(parsed, "gelir")

        self.assertEqual(records[0][0]["donem"], "2026 - 1. GEÇİCİ")

    def test_gecici_vergi_pdf_is_classified_before_annual_return(self):
        self.assertTrue(is_gecici_vergi_pdf("GEÇİCİ VERGİ BEYANNAMESİ"))
        self.assertFalse(is_gecici_vergi_pdf("KURUMLAR VERGİSİ BEYANNAMESİ"))

    def test_income_only_period_calculates_profitability_ratios(self):
        gelir_df = pd.DataFrame(
            [
                {"Kod": "", "Açıklama": "A. Brüt Satışlar", "Cari Dönem": 257114582.09},
                {"Kod": "", "Açıklama": "B. Satış İndirimleri (-)", "Cari Dönem": -3683731.92},
                {"Kod": "", "Açıklama": "D. Satışların Maliyeti (-)", "Cari Dönem": -228795154.20},
                {"Kod": "", "Açıklama": "E. Faaliyet Giderleri (-)", "Cari Dönem": -8752084.70},
                {"Kod": "", "Açıklama": "F. Diğer Faaliyetlerden Olağan Gelir ve Karlar", "Cari Dönem": 3085519.17},
                {"Kod": "", "Açıklama": "H. Finansman Giderleri (-)", "Cari Dönem": -1269230.44},
                {"Kod": "", "Açıklama": "J. Olağandışı Gider ve Zararlar (-)", "Cari Dönem": -1459563.44},
                {"Kod": "", "Açıklama": "Dönem Net Karı veya Zararı", "Cari Dönem": 16240336.56},
            ]
        )

        ratios = _calculate_available_financial_ratios(None, None, gelir_df)

        self.assertEqual(ratios["Faaliyet Kar Marjı"]["deger"], 6.27)
        self.assertEqual(ratios["Net Kar Marjı (Satışların Karlılığı)"]["deger"], 6.41)
        self.assertNotIn("Cari Oran", ratios)

    def test_truncated_income_tax_provision_label_is_expanded(self):
        rows = [
            {
                "kod": "",
                "aciklama": "K. Dönem Karı, Vergi ve Diğer Yasal Yükümlülük",
                "cari_donem": 2826551.83,
            },
            {
                "kod": "621",
                "aciklama": "Satılan Ticari Mallar Maliyeti (-)",
                "cari_donem": 0.0,
            },
        ]

        normalized = canonicalize_gelir_rows(rows)

        self.assertEqual(
            normalized[0]["aciklama"],
            "K. Dönem Karı, Vergi ve Diğer Yasal Yükümlülük Karşılıkları (-)",
        )
        self.assertEqual(
            normalized[1]["aciklama"],
            "Satılan Ticari Mallar Maliyeti (-)",
        )

    def test_current_filing_does_not_create_or_overwrite_previous_year(self):
        parsed = {
            "donem": "Aralık / 2025",
            "has_inflation": False,
            "aktif": [
                {
                    "Kod": "100",
                    "Açıklama": "Kasa",
                    "Önceki Dönem": 100.0,
                    "Cari Dönem": 200.0,
                }
            ],
            "pasif": [
                {
                    "Kod": "300",
                    "Açıklama": "Banka Kredileri",
                    "Önceki Dönem": 100.0,
                    "Cari Dönem": 200.0,
                }
            ],
        }

        records = process_parsed_parts(parsed, "bilanco")

        self.assertEqual(len(records), 1)
        data, document_type, _ = records[0]
        self.assertEqual(data["donem"], "2025")
        self.assertEqual(document_type, "bilanco")
        self.assertEqual(data["aktif"][0]["Önceki Dönem"], 100.0)

    def test_2023_normal_and_inflation_values_share_one_record(self):
        parsed = {
            "donem": "Aralık / 2023",
            "has_inflation": True,
            "aktif": [
                {
                    "Kod": "100",
                    "Açıklama": "Kasa",
                    "Önceki Dönem": 461000.61,
                    "Cari Dönem": 276891.54,
                    "Cari Dönem (Enflasyonlu)": 276891.54,
                }
            ],
            "pasif": [],
        }

        records = process_parsed_parts(parsed, "bilanco")
        data = records[0][0]

        self.assertEqual(len(records), 1)
        self.assertTrue(data["has_inflation"])
        self.assertEqual(data["aktif"][0]["Cari Dönem"], 276891.54)
        self.assertEqual(
            data["aktif"][0]["Cari Dönem (Enflasyonlu)"],
            276891.54,
        )

    def test_unknown_period_is_rejected_instead_of_defaulting_to_2023(self):
        with self.assertRaisesRegex(ValueError, "hesap dönemi"):
            process_parsed_parts(
                {"donem": "Bilinmiyor", "aktif": [], "pasif": []},
                "bilanco",
            )


if __name__ == "__main__":
    unittest.main()
