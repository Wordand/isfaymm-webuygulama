import unittest

from hesaplar import BILANCO_HESAPLARI
from services.pdf_service import canonicalize_gelir_rows
from services.excel_service import (
    _build_balance_table,
    _build_income_table,
    _build_validation,
    _current_period_result_for_balance,
    _normalize_account_code,
    _repair_pdf_row,
    build_mizan_report_comparison,
    build_mizan_tax_checks,
)


def account(code, debit=0.0, credit=0.0, debit_balance=0.0, credit_balance=0.0):
    return {
        "code": code,
        "description": code,
        "debit": debit,
        "credit": credit,
        "debit_balance": debit_balance,
        "credit_balance": credit_balance,
    }


class MizanParsingTests(unittest.TestCase):
    def test_mizan_income_rows_are_converted_for_income_template(self):
        rows = canonicalize_gelir_rows([
            {"Kod": "600", "Açıklama": "Yurtiçi Satışlar", "Cari Dönem": 253_430_850.17},
            {"Kod": "", "Açıklama": "C. NET SATIŞLAR", "Cari Dönem": 253_430_850.17},
        ])

        self.assertEqual(rows[0]["kod"], "600")
        self.assertEqual(rows[0]["aciklama"], "Yurtiçi Satışlar")
        self.assertEqual(rows[0]["cari_donem"], 253_430_850.17)
        self.assertEqual(rows[1]["aciklama"], "C. NET SATIŞLAR")

    def test_description_starting_with_number_is_not_an_account_code(self):
        self.assertIsNone(_normalize_account_code("60 CM 4 KT 10 MM KONVEYOR BANT"))
        self.assertEqual(_normalize_account_code("770 00 029")["main_code"], "770")

    def test_closed_income_accounts_use_natural_movement_side(self):
        accounts = [
            account("600", debit=257_114_582.09, credit=257_114_582.09),
            account("610", debit=3_683_731.92, credit=3_683_731.92),
            account("620", debit=228_795_154.20, credit=228_795_154.20),
            account("631", debit=2_228_776.10, credit=2_228_776.10),
            account("632", debit=6_523_308.60, credit=6_523_308.60),
            account("649", debit=3_085_519.17, credit=3_085_519.17),
            account("660", debit=1_269_230.44, credit=1_269_230.44),
            account("689", debit=1_459_563.44, credit=1_459_563.44),
            account("690", credit_balance=16_240_336.56),
        ]

        _, summary = _build_income_table(accounts)

        self.assertAlmostEqual(summary["net_sales"], 253_430_850.17, places=2)
        self.assertAlmostEqual(summary["derived_period_profit"], 16_240_336.56, places=2)
        self.assertAlmostEqual(summary["period_profit"], 16_240_336.56, places=2)

    def test_overlapped_reflection_row_uses_credit_movement(self):
        repaired = _repair_pdf_row([
            "711",
            "DİREKT İLK MADDE VE MALZEME GİD.YANSITMA",
            "N.HE1S8.5.996.960,75",
            "185.996.960,75",
            "",
            "",
        ])

        self.assertEqual(repaired[2], "185.996.960,75")
        self.assertEqual(repaired[3], "185.996.960,75")

    def test_untransferred_period_profit_completes_passive_equity(self):
        accounts = [
            account("100", debit_balance=100.0),
            account("300", credit_balance=80.0),
            account("690", credit_balance=20.0),
        ]
        _, income_summary = _build_income_table(accounts)
        current_result = _current_period_result_for_balance(accounts, income_summary)
        passive = _build_balance_table(
            BILANCO_HESAPLARI["PASİF"],
            accounts,
            "PASİF",
            current_period_result=current_result,
        )
        validation, totals = _build_validation(
            accounts,
            {},
            income_summary,
            current_period_result=current_result,
        )

        period_row = next(row for row in passive if row["Kod"] == "590")
        statement_check = next(row for row in validation if row["code"] == "statement_equality")

        self.assertEqual(current_result, 20.0)
        self.assertEqual(period_row["Cari Dönem"], 20.0)
        self.assertEqual(totals["passive_total"], 100.0)
        self.assertEqual(statement_check["status"], "success")

    def test_unrelated_balance_difference_is_not_hidden(self):
        accounts = [
            account("100", debit_balance=100.0),
            account("300", credit_balance=70.0),
            account("690", credit_balance=20.0),
        ]
        _, income_summary = _build_income_table(accounts)

        self.assertEqual(_current_period_result_for_balance(accounts, income_summary), 0.0)

    def test_saved_mizan_rows_receive_extended_tax_checks(self):
        raw_rows = [
            {
                "Hesap Kodu": "689 09",
                "Ana Hesap": "689",
                "Açıklama": "Vergi cezası KKEG",
                "Borç": 1_000.0,
                "Alacak": 1_000.0,
                "Borç Bakiye": 0.0,
                "Alacak Bakiye": 0.0,
            },
        ]
        summary_accounts = [
            account("300", credit_balance=300_000.0),
            account("331", credit_balance=50_000.0),
            account("500", credit_balance=100_000.0),
            account("660", debit=12_500.0, credit=12_500.0),
            account("689", debit=1_000.0, credit=1_000.0),
        ]

        checks = build_mizan_tax_checks(raw_rows, summary_accounts)
        by_code = {item["code"]: item for item in checks}

        self.assertIn("kkeg_candidates", by_code)
        self.assertIn("penalty_expenses", by_code)
        self.assertIn("account_331", by_code)
        self.assertEqual(by_code["financing_expenses"]["status"], "warning")
        self.assertEqual(by_code["penalty_expenses"]["basis"], "KVK 11/1-d")

    def test_mizan_comparison_uses_newly_loaded_provisional_income(self):
        reports = {
            "gelir": {
                "tablo": [
                    {"Açıklama": "C. Net Satışlar", "cari_donem": 253_430_850.17},
                    {"Açıklama": "Dönem Karı veya Zararı", "cari_donem": 16_240_336.56},
                ],
            },
        }
        parsed = {
            "summary": {
                "active_total": 400_067_883.67,
                "passive_total": 400_067_883.66,
                "net_sales": 253_430_850.17,
                "period_profit": 16_240_336.56,
            },
        }

        comparison = build_mizan_report_comparison(reports, parsed)

        self.assertEqual([item["title"] for item in comparison], ["Net satışlar", "Dönem kârı veya zararı"])
        self.assertTrue(all(item["status"] == "success" for item in comparison))


if __name__ == "__main__":
    unittest.main()
