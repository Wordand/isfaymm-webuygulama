import math
import os
import re
import unicodedata
from collections import defaultdict

import pandas as pd

from .utils import to_float_turkish
from gelir import GELIR_TABLOSU_HESAPLARI
from hesaplar import BILANCO_HESAPLARI


MIZAN_TOLERANCE = 1.0

NEGATIVE_BILANCO_CODES = {
    "103", "119", "122", "124", "129", "137", "139", "158",
    "199", "222", "224", "229", "237", "239", "241", "243",
    "244", "246", "247", "249", "257", "268", "278", "298",
    "299", "302", "308", "322", "337", "371", "402", "408",
    "422", "437", "501", "503", "580", "591",
}

REFLECTION_CODES = {"711", "721", "731", "741", "751", "761", "771", "781"}

PDF_TABLE_SETTINGS = {
    "vertical_strategy": "lines",
    "horizontal_strategy": "text",
    "intersection_tolerance": 5,
    "snap_tolerance": 3,
    "join_tolerance": 3,
}


def _text(value):
    if value is None:
        return ""
    if isinstance(value, float):
        if math.isnan(value):
            return ""
        if value.is_integer():
            return str(int(value))
    return re.sub(r"\s+", " ", str(value)).strip()


def _number(value):
    return float(to_float_turkish(value) or 0)


def _normalize_account_code(value):
    raw = _text(value)
    if not raw:
        return None

    # Hesap kodu hücresi yalnızca rakam ve hesap ayırıcılarından oluşmalıdır.
    # "60 CM 4 KT..." gibi rakamla başlayan açıklamalar hesap kodu değildir.
    if not re.fullmatch(r"(?:\d{3,}|\d{3}(?:[\s./-]+\d+)+)", raw):
        return None

    groups = re.findall(r"\d+", raw)
    if not groups:
        return None

    compact = "".join(groups)
    if len(compact) < 3:
        return None

    main_code = compact[:3]
    if not main_code.isdigit() or main_code[0] not in "123456789":
        return None

    if len(groups[0]) > 3:
        remainder = groups[0][3:]
        groups = [groups[0][:3]] + ([remainder] if remainder else []) + groups[1:]
    elif len(groups[0]) < 3:
        groups = [main_code] + ([compact[3:]] if compact[3:] else [])

    return {
        "raw_code": raw,
        "main_code": main_code,
        "code_key": compact,
        "segments": tuple(part for part in groups if part),
        "level": max(1, len(tuple(part for part in groups if part))),
    }


def detect_mizan_metadata_from_text(text):
    text = str(text or "")
    metadata = {"detected_period": "", "detected_title": ""}

    date_match = re.search(
        r"(\d{2})[./](\d{2})[./](20\d{2})\s*-\s*(\d{2})[./](\d{2})[./](20\d{2})",
        text,
    )
    if date_match:
        start_month = int(date_match.group(2))
        end_month = int(date_match.group(5))
        year = date_match.group(6)
        quarter_by_month = {3: 1, 6: 2, 9: 3}
        if end_month == 12 and date_match.group(3) == year:
            metadata["detected_period"] = year
        elif date_match.group(3) == year and start_month in {1, 4, 7} and end_month in quarter_by_month:
            metadata["detected_period"] = f"{year} - {quarter_by_month[end_month]}. GEÇİCİ"
        else:
            metadata["detected_period"] = year
    else:
        year_match = re.search(r"\b(20\d{2})\b", text)
        if year_match:
            metadata["detected_period"] = year_match.group(1)

    lines = [_text(line) for line in text.splitlines() if _text(line)]
    for index, line in enumerate(lines):
        if re.search(r"\bM[İI]ZAN\b", line, re.I) and index + 1 < len(lines):
            candidate = lines[index + 1]
            if not re.search(r"SAYFA|HESAP KODU", candidate, re.I):
                metadata["detected_title"] = candidate
                break

    return metadata


def _is_amount_text(value):
    value = _text(value)
    return bool(re.fullmatch(r"\(?-?\d[\d.]*,\d{2}\)?|-?\d+(?:\.\d+)?", value))


def _repair_pdf_row(cells):
    cells = [_text(cell) for cell in list(cells or [])]
    if len(cells) < 6:
        cells += [""] * (6 - len(cells))
    cells = cells[:6]

    description_parts = [cells[1]]
    amount_pattern = re.compile(r"(\(?-?\d[\d.]*,\d{2}\)?)$")

    for index in range(2, 6):
        value = cells[index]
        if not value or _is_amount_text(value):
            continue
        match = amount_pattern.search(value)
        if match:
            prefix = value[:match.start()].strip()
            if prefix:
                description_parts.append(prefix)
            cells[index] = match.group(1)
        else:
            description_parts.append(value)
            cells[index] = ""

    cells[1] = _text(" ".join(description_parts))

    # Bazı PDF'lerde uzun yansıtma hesabı açıklaması borç tutarıyla üst üste gelir.
    # Kapanmış yansıtma satırında bakiye yoksa iki hareket sütunu eşit olmalıdır.
    code_info = _normalize_account_code(cells[0])
    if (
        code_info
        and code_info["main_code"] in REFLECTION_CODES
        and cells[3]
        and not cells[4]
        and not cells[5]
        and abs(_number(cells[2]) - _number(cells[3])) > MIZAN_TOLERANCE
    ):
        cells[2] = cells[3]

    return cells


def _extract_excel_rows(excel_path):
    raw = pd.read_excel(excel_path, header=None)
    if raw.shape[1] < 6:
        raise ValueError("Mizan dosyasında KOD, AÇIKLAMA, BORÇ, ALACAK, BORÇ BAKİYE ve ALACAK BAKİYE sütunları bulunmalıdır.")

    header_index = None
    for index in range(min(len(raw), 25)):
        row_text = " ".join(_text(value).upper() for value in raw.iloc[index, :6].tolist())
        if ("HESAP" in row_text or "KOD" in row_text) and "BOR" in row_text and "ALACAK" in row_text:
            header_index = index
            break

    start_index = header_index + 1 if header_index is not None else 0
    source_rows = []
    general_totals = None

    for _, row in raw.iloc[start_index:, :6].iterrows():
        cells = row.tolist()
        code_text = _text(cells[0])
        description = _text(cells[1])
        combined = f"{code_text} {description}".upper()
        if "GENEL TOPLAM" in combined:
            general_totals = {
                "debit": _number(cells[2]),
                "credit": _number(cells[3]),
                "debit_balance": _number(cells[4]),
                "credit_balance": _number(cells[5]),
            }
            continue
        source_rows.append(cells)

    return source_rows, {"source_format": "excel", "general_totals": general_totals}


def _extract_pdf_rows(pdf_path):
    try:
        import pdfplumber
    except ImportError as exc:
        raise ValueError("PDF mizan okuyucusu kullanılamıyor.") from exc

    source_rows = []
    general_totals = None
    full_text_parts = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            full_text_parts.append(page_text)
            table = page.extract_table(PDF_TABLE_SETTINGS) or []

            for table_row in table:
                cells = list(table_row or [])
                if len(cells) == 5 and not _text(cells[0]) and any(_text(cell) for cell in cells[1:]):
                    general_totals = {
                        "debit": _number(cells[1]),
                        "credit": _number(cells[2]),
                        "debit_balance": _number(cells[3]),
                        "credit_balance": _number(cells[4]),
                    }
                    continue

                cells = _repair_pdf_row(cells)
                header_text = " ".join(cells).upper()
                if "HESAP KODU" in header_text or ("AÇIKLAMA" in header_text and "BORÇ" in header_text):
                    continue
                if not _normalize_account_code(cells[0]):
                    continue
                source_rows.append(cells)

    full_text = "\n".join(full_text_parts)
    if not re.search(r"\bM[İI]ZAN\b", full_text, re.I):
        raise ValueError("PDF içinde mizan başlığı bulunamadı.")

    metadata = detect_mizan_metadata_from_text(full_text)
    metadata.update({"source_format": "pdf", "general_totals": general_totals})
    return source_rows, metadata


def _normalize_source_rows(source_rows):
    normalized = []
    for cells in source_rows:
        cells = list(cells or []) + [""] * 6
        code_info = _normalize_account_code(cells[0])
        if not code_info:
            continue

        debit = _number(cells[2])
        credit = _number(cells[3])
        debit_balance = _number(cells[4])
        credit_balance = _number(cells[5])

        if abs(debit_balance) <= MIZAN_TOLERANCE and abs(credit_balance) <= MIZAN_TOLERANCE:
            transaction_balance = debit - credit
            if transaction_balance > MIZAN_TOLERANCE:
                debit_balance = transaction_balance
            elif transaction_balance < -MIZAN_TOLERANCE:
                credit_balance = abs(transaction_balance)

        normalized.append({
            **code_info,
            "description": _text(cells[1]) or code_info["raw_code"],
            "debit": debit,
            "credit": credit,
            "debit_balance": debit_balance,
            "credit_balance": credit_balance,
        })

    if not normalized:
        raise ValueError("Mizan içinde okunabilir hesap satırı bulunamadı.")
    return normalized


def _is_descendant(candidate, parent):
    return len(candidate) > len(parent) and candidate[:len(parent)] == parent


def _aggregate_main_accounts(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["main_code"]].append(row)

    summary = []
    parent_groups = 0
    leaf_groups = 0
    ignored_detail_rows = 0

    for main_code, group_rows in grouped.items():
        exact_rows = [row for row in group_rows if row["code_key"] == main_code]
        if exact_rows:
            selected = exact_rows
            parent_groups += 1
            ignored_detail_rows += max(0, len(group_rows) - len(exact_rows))
            aggregation_source = "ana_hesap"
        else:
            selected = [
                row for row in group_rows
                if not any(
                    _is_descendant(other["segments"], row["segments"])
                    for other in group_rows
                    if other is not row
                )
            ]
            leaf_groups += 1
            ignored_detail_rows += max(0, len(group_rows) - len(selected))
            aggregation_source = "alt_hesap_toplami"

        summary.append({
            "code": main_code,
            "description": selected[0]["description"] if selected else group_rows[0]["description"],
            "debit": sum(row["debit"] for row in selected),
            "credit": sum(row["credit"] for row in selected),
            "debit_balance": sum(row["debit_balance"] for row in selected),
            "credit_balance": sum(row["credit_balance"] for row in selected),
            "aggregation_source": aggregation_source,
            "selected_row_count": len(selected),
            "detail_row_count": len(group_rows),
        })

    return sorted(summary, key=lambda row: row["code"]), {
        "parent_groups": parent_groups,
        "leaf_groups": leaf_groups,
        "ignored_detail_rows": ignored_detail_rows,
    }


def _balance_amount(account):
    code = account["code"]
    if code.startswith(("1", "2")):
        return account["debit_balance"] - account["credit_balance"]
    if code.startswith(("3", "4", "5")):
        return account["credit_balance"] - account["debit_balance"]
    return 0.0


def _income_amount(account):
    balance_amount = account["credit_balance"] - account["debit_balance"]
    if abs(balance_amount) > MIZAN_TOLERANCE:
        return balance_amount

    # Dönem sonu kapanışları yapılmış mizanda 6xx hesapların bakiyesi sıfırdır.
    # Gelir tablosu bu durumda hesabın doğal hareket yönünden oluşturulur.
    code = int(account["code"])
    if 600 <= code <= 609 or 640 <= code <= 649 or 670 <= code <= 679:
        return account["credit"]
    if 610 <= code <= 639 or 650 <= code <= 669 or 680 <= code <= 689 or code == 691:
        return -account["debit"]
    return balance_amount


def _all_structure_codes(structure):
    codes = set()
    for subgroups in structure.values():
        for accounts in subgroups.values():
            codes.update(accounts.keys())
    return codes


def _build_balance_table(structure, summary_accounts, side, current_period_result=0.0):
    account_map = {row["code"]: row for row in summary_accounts}
    amount_map = {code: _balance_amount(row) for code, row in account_map.items()}
    known_codes = _all_structure_codes(structure)
    prefix_map = {
        "I.": "1", "II.": "2", "III.": "3", "IV.": "4", "V.": "5",
    }
    output = []

    for group_name, subgroups in structure.items():
        prefix = next((value for key, value in prefix_map.items() if group_name.startswith(key)), "")
        group_codes = [code for code in account_map if prefix and code.startswith(prefix)]
        group_adjustment = (
            current_period_result
            if side == "PASİF" and group_name.startswith("V.")
            else 0.0
        )
        group_total = sum(amount_map.get(code, 0) for code in group_codes) + group_adjustment
        output.append({"Kod": "", "Açıklama": group_name, "Cari Dönem": group_total})

        for subgroup_name, accounts in subgroups.items():
            present_codes = [code for code in accounts if code in account_map]
            subgroup_adjustment = (
                current_period_result
                if group_adjustment and subgroup_name.startswith("F. Dönem Net")
                else 0.0
            )
            if not present_codes and not subgroup_adjustment:
                continue
            subgroup_total = sum(amount_map.get(code, 0) for code in present_codes) + subgroup_adjustment
            output.append({"Kod": "", "Açıklama": subgroup_name, "Cari Dönem": subgroup_total})
            for code in present_codes:
                row_amount = amount_map.get(code, 0)
                if subgroup_adjustment and code == ("590" if subgroup_adjustment > 0 else "591"):
                    row_amount += subgroup_adjustment
                output.append({
                    "Kod": code,
                    "Açıklama": accounts[code],
                    "Cari Dönem": row_amount,
                })

            if subgroup_adjustment:
                result_code = "590" if subgroup_adjustment > 0 else "591"
                if result_code not in present_codes:
                    output.append({
                        "Kod": result_code,
                        "Açıklama": accounts[result_code],
                        "Cari Dönem": subgroup_adjustment,
                    })

        unmatched = [
            code for code in group_codes
            if code not in known_codes and abs(amount_map.get(code, 0)) > MIZAN_TOLERANCE
        ]
        if unmatched:
            output.append({
                "Kod": "",
                "Açıklama": "Diğer / Eşleştirilemeyen Hesaplar",
                "Cari Dönem": sum(amount_map[code] for code in unmatched),
            })
            for code in unmatched:
                output.append({
                    "Kod": code,
                    "Açıklama": account_map[code]["description"],
                    "Cari Dönem": amount_map[code],
                })

    return output


def _current_period_result_for_balance(summary_accounts, income_summary):
    active_total = sum(
        _balance_amount(row)
        for row in summary_accounts
        if row["code"].startswith(("1", "2"))
    )
    passive_total = sum(
        _balance_amount(row)
        for row in summary_accounts
        if row["code"].startswith(("3", "4", "5"))
    )
    current_period_result = income_summary.get("net_profit", 0.0)

    # Geçici mizanda 690 kapanış bakiyesi oluşmuş, ancak sonuç henüz 590/591'e
    # devredilmemiş olabilir. Yalnızca bilanço farkı sonuçla mutabık olduğunda
    # bu tutarı özkaynaklarda göster; başka bir farkı otomatik kapatma.
    if (
        abs(current_period_result) > MIZAN_TOLERANCE
        and abs((active_total - passive_total) - current_period_result) <= MIZAN_TOLERANCE
    ):
        return current_period_result
    return 0.0


def _build_income_table(summary_accounts):
    account_map = {row["code"]: row for row in summary_accounts if row["code"].startswith("6")}
    values = {code: _income_amount(row) for code, row in account_map.items()}

    def total(*codes):
        return sum(values.get(code, 0) for code in codes)

    brut_satislar = total("600", "601", "602")
    satis_indirimleri = total("610", "611", "612")
    net_satislar = brut_satislar + satis_indirimleri
    satislarin_maliyeti = total("620", "621", "622", "623")
    brut_kar = net_satislar + satislarin_maliyeti
    faaliyet_giderleri = total("630", "631", "632")
    faaliyet_kari = brut_kar + faaliyet_giderleri
    olagan_gelirler = total(*[str(code) for code in range(640, 650)])
    olagan_giderler = total(*[str(code) for code in range(653, 660)])
    finansman_giderleri = total("660", "661")
    olagan_kar = faaliyet_kari + olagan_gelirler + olagan_giderler + finansman_giderleri
    olagandisi_gelirler = total("671", "679")
    olagandisi_giderler = total("680", "681", "689")
    derived_period_profit = olagan_kar + olagandisi_gelirler + olagandisi_giderler
    closing_profit = values.get("690")
    period_profit = (
        closing_profit
        if closing_profit is not None and abs(closing_profit) > MIZAN_TOLERANCE
        else derived_period_profit
    )
    tax_provision = values.get("691", 0)
    closing_net_profit = values.get("692")
    net_profit = (
        closing_net_profit
        if closing_net_profit is not None and abs(closing_net_profit) > MIZAN_TOLERANCE
        else period_profit + tax_provision
    )

    calculated = {
        "A. BRÜT SATIŞLAR": brut_satislar,
        "B. SATIŞ İNDİRİMLERİ (-)": satis_indirimleri,
        "C. NET SATIŞLAR": net_satislar,
        "D. SATIŞLARIN MALİYETİ (-)": satislarin_maliyeti,
        "BRÜT SATIŞ KARI VEYA ZARARI": brut_kar,
        "E. FAALİYET GİDERLERİ (-)": faaliyet_giderleri,
        "FAALİYET KARI VEYA ZARARI": faaliyet_kari,
        "F. DİĞER FAALİYETLERDEN OLAĞAN GELİR VE KARLAR": olagan_gelirler,
        "G. DİĞER FAALİYETLERDEN OLAĞAN GİDERLER VE ZARARLAR (-)": olagan_giderler,
        "H. FİNANSMAN GİDERLERİ (-)": finansman_giderleri,
        "OLAĞAN KAR VEYA ZARAR": olagan_kar,
        "I. OLAĞANDIŞI GELİR VE KARLAR": olagandisi_gelirler,
        "J. OLAĞANDIŞI GİDER VE ZARARLAR (-)": olagandisi_giderler,
        "DÖNEM KARI VEYA ZARARI": period_profit,
        "K. DÖNEM KARI, VERGİ VE DİĞER YASAL YÜKÜMLÜLÜK KARŞILIKLARI (-)": tax_provision,
        "DÖNEM NET KARI VEYA ZARARI": net_profit,
    }

    output = []
    mapped_codes = set()
    for group_name, codes in GELIR_TABLOSU_HESAPLARI.items():
        output.append({"Kod": "", "Açıklama": group_name, "Cari Dönem": calculated[group_name]})
        for code, description in codes.items():
            mapped_codes.add(code)
            if code in account_map:
                output.append({"Kod": code, "Açıklama": description, "Cari Dönem": values[code]})

        if group_name == "DÖNEM KARI VEYA ZARARI" and "690" in account_map:
            mapped_codes.add("690")
            output.append({"Kod": "690", "Açıklama": "Dönem Kârı veya Zararı", "Cari Dönem": values["690"]})
        elif group_name.startswith("K. ") and "691" in account_map:
            mapped_codes.add("691")
            output.append({"Kod": "691", "Açıklama": "Dönem Kârı Vergi ve Diğer Yasal Yükümlülük Karşılıkları (-)", "Cari Dönem": values["691"]})
        elif group_name == "DÖNEM NET KARI VEYA ZARARI" and "692" in account_map:
            mapped_codes.add("692")
            output.append({"Kod": "692", "Açıklama": "Dönem Net Kârı veya Zararı", "Cari Dönem": values["692"]})

    unmatched = [code for code in account_map if code not in mapped_codes and code not in {"690", "691", "692"}]
    for code in unmatched:
        if abs(values.get(code, 0)) > MIZAN_TOLERANCE:
            output.append({"Kod": code, "Açıklama": account_map[code]["description"], "Cari Dönem": values[code]})

    return output, {
        "gross_sales": brut_satislar,
        "net_sales": net_satislar,
        "derived_period_profit": derived_period_profit,
        "period_profit": period_profit,
        "net_profit": net_profit,
    }


def _build_validation(summary_accounts, metadata, income_summary, current_period_result=0.0):
    general_totals = metadata.get("general_totals") or {}
    debit_total = general_totals.get("debit") or sum(row["debit"] for row in summary_accounts)
    credit_total = general_totals.get("credit") or sum(row["credit"] for row in summary_accounts)
    debit_balance = general_totals.get("debit_balance") or sum(row["debit_balance"] for row in summary_accounts)
    credit_balance = general_totals.get("credit_balance") or sum(row["credit_balance"] for row in summary_accounts)

    transaction_difference = round(debit_total - credit_total, 2)
    balance_difference = round(debit_balance - credit_balance, 2)
    active_total = sum(_balance_amount(row) for row in summary_accounts if row["code"].startswith(("1", "2")))
    passive_total = (
        sum(_balance_amount(row) for row in summary_accounts if row["code"].startswith(("3", "4", "5")))
        + current_period_result
    )
    statement_difference = round(active_total - passive_total, 2)
    has_active_accounts = any(row["code"].startswith(("1", "2")) for row in summary_accounts)
    has_passive_accounts = any(row["code"].startswith(("3", "4", "5")) for row in summary_accounts)
    has_income_accounts = any(row["code"].startswith("6") for row in summary_accounts)
    has_complete_statement_scope = has_active_accounts and has_passive_accounts

    missing_sections = []
    if not has_active_accounts:
        missing_sections.append("aktif hesaplar (1xx-2xx)")
    if not has_passive_accounts:
        missing_sections.append("pasif hesaplar (3xx-5xx)")
    if not has_income_accounts:
        missing_sections.append("gelir tablosu hesapları (6xx)")

    validations = [
        {
            "code": "transaction_equality",
            "title": "Borç ve alacak toplamı",
            "status": "success" if abs(transaction_difference) <= MIZAN_TOLERANCE else "warning",
            "detail": f"Fark {abs(transaction_difference):,.2f} TL. En fazla {MIZAN_TOLERANCE:,.2f} TL yuvarlama farkı kabul edilir.",
            "difference": transaction_difference,
        },
        {
            "code": "balance_equality",
            "title": "Borç ve alacak bakiyeleri",
            "status": "success" if abs(balance_difference) <= MIZAN_TOLERANCE else "warning",
            "detail": f"Bakiye farkı {abs(balance_difference):,.2f} TL.",
            "difference": balance_difference,
        },
        {
            "code": "statement_equality",
            "title": "Oluşturulan bilanço eşitliği",
            "status": "success" if has_complete_statement_scope and abs(statement_difference) <= MIZAN_TOLERANCE else "warning",
            "detail": (
                f"Aktif ile pasif arasındaki fark {abs(statement_difference):,.2f} TL."
                if has_complete_statement_scope
                else "Aktif veya pasif hesap sınıfları eksik olduğu için bilanço eşitliği doğrulanamadı."
            ),
            "difference": statement_difference,
        },
        {
            "code": "financial_statement_coverage",
            "title": "Mali tablo kapsamı",
            "status": "success" if not missing_sections else "warning",
            "detail": (
                "Bilanço ve gelir tablosu için gerekli hesap sınıfları dosyada bulundu."
                if not missing_sections
                else "Dosyada şu bölümler bulunmadı: " + ", ".join(missing_sections) + ". Tam mali tablo için mizan dosyasının tüm sayfaları yüklenmelidir."
            ),
            "difference": 0,
        },
    ]

    account_690 = next((row for row in summary_accounts if row["code"] == "690"), None)
    if account_690:
        closing_profit = _income_amount(account_690)
        profit_difference = round(closing_profit - income_summary["derived_period_profit"], 2)
        validations.append({
            "code": "period_profit_reconciliation",
            "title": "690 hesap mutabakatı",
            "status": "success" if abs(profit_difference) <= MIZAN_TOLERANCE else "warning",
            "detail": f"690 hesap ile gelir tablosundan türetilen dönem sonucu arasındaki fark {abs(profit_difference):,.2f} TL.",
            "difference": profit_difference,
        })

    return validations, {
        "debit_total": debit_total,
        "credit_total": credit_total,
        "debit_balance_total": debit_balance,
        "credit_balance_total": credit_balance,
        "active_total": active_total,
        "passive_total": passive_total,
        "statement_difference": statement_difference,
        "current_period_result_added": current_period_result,
        "has_active_accounts": has_active_accounts,
        "has_passive_accounts": has_passive_accounts,
        "has_income_accounts": has_income_accounts,
        "has_complete_balance": has_complete_statement_scope,
    }


def _normalise_saved_mizan_rows(raw_rows):
    """Kayıtlı JSON satırlarını ayrıştırıcının iç biçimine dönüştürür."""
    normalised = []
    for row in raw_rows or []:
        if "description" in row:
            normalised.append(row)
            continue

        raw_code = _text(row.get("Hesap Kodu", row.get("raw_code", "")))
        code_info = _normalize_account_code(raw_code)
        main_code = _text(row.get("Ana Hesap", row.get("main_code", "")))
        if not code_info and main_code:
            code_info = _normalize_account_code(main_code)
        if not code_info:
            continue

        normalised.append({
            **code_info,
            "description": _text(row.get("Açıklama", row.get("description", raw_code))),
            "debit": _number(row.get("Borç", row.get("debit", 0))),
            "credit": _number(row.get("Alacak", row.get("credit", 0))),
            "debit_balance": _number(row.get("Borç Bakiye", row.get("debit_balance", 0))),
            "credit_balance": _number(row.get("Alacak Bakiye", row.get("credit_balance", 0))),
        })
    return normalised


def _expense_row_amount(row):
    balance = float(row.get("debit_balance", 0)) - float(row.get("credit_balance", 0))
    if balance > MIZAN_TOLERANCE:
        return balance
    return max(float(row.get("debit", 0)), 0)


def _account_net_amount(account):
    return abs(float(account.get("debit_balance", 0)) - float(account.get("credit_balance", 0)))


def _build_tax_checks(raw_rows, summary_accounts):
    account_map = {row["code"]: row for row in summary_accounts or []}
    checks = []

    def add_check(code, title, status, detail, *, category, accounts=None,
                  amount=0, basis="", action=""):
        amount_labels = {
            "reflection_accounts": "Açık bakiye toplamı",
            "kkeg_candidates": "KKEG adayı tutar",
            "penalty_expenses": "Kontrole konu gider",
            "donation_expenses": "Kontrole konu gider",
            "vehicle_expenses": "Kontrole konu gider",
            "account_368": "Hesap bakiyesi",
            "account_131": "Ortaklardan alacak",
            "account_331": "Ortaklara borç",
            "vat_accounts": "KDV hesap bakiyeleri",
            "tax_provision_accounts": "Vergi hesap bakiyeleri",
            "financing_expenses": "Finansman gideri toplamı",
            "doubtful_receivables": "Şüpheli alacak tutarı",
            "fixed_asset_depreciation": "Birikmiş amortisman",
            "periodisation_accounts": "Dönemsellik hesapları",
            "foreign_currency_valuation": "Kambiyo hareketleri",
            "inflation_adjustment": "Düzeltme hesapları",
        }
        checks.append({
            "code": code,
            "title": title,
            "status": status,
            "detail": detail,
            "category": category,
            "accounts": accounts or [],
            "amount": float(amount or 0),
            "amount_label": amount_labels.get(code, "Kontrole konu tutar"),
            "basis": basis,
            "action": action,
        })

    def matching_rows(pattern, prefixes=("6", "7", "8")):
        matched = [
            row for row in raw_rows
            if str(row.get("main_code", "")).startswith(prefixes)
            and re.search(pattern, row.get("description", ""), re.I)
        ]
        return [
            row for row in matched
            if not any(
                other is not row and _is_descendant(other.get("segments", ()), row.get("segments", ()))
                for other in matched
            )
        ]

    open_reflections = []
    for code in sorted(REFLECTION_CODES):
        account = account_map.get(code)
        if account:
            net_balance = account["debit_balance"] - account["credit_balance"]
            if abs(net_balance) > MIZAN_TOLERANCE:
                open_reflections.append((code, net_balance))
    add_check(
        "reflection_accounts",
        "Yansıtma hesapları",
        "warning" if open_reflections else "success",
        (
            "Açık bakiye veren yansıtma hesapları tespit edildi."
            if open_reflections else "Kontrol edilen yansıtma hesaplarında açık bakiye görülmedi."
        ),
        category="Muhasebe kapanışı",
        accounts=[code for code, _ in open_reflections],
        amount=sum(abs(value) for _, value in open_reflections),
        basis="Tek Düzen Hesap Planı kapanış kontrolü",
        action="Açık bakiye varsa ilgili gider ve yansıtma hesaplarının kapanış kayıtlarını karşılaştırın.",
    )

    kkeg_rows = matching_rows(r"KANUNEN KABUL EDİLMEYEN|\bKKEG\b", prefixes=("6", "7", "8"))
    if kkeg_rows:
        add_check(
            "kkeg_candidates",
            "KKEG olarak işaretlenen hesaplar",
            "info",
            f"Açıklamasında KKEG ifadesi bulunan {len(kkeg_rows)} hesap satırı tespit edildi.",
            category="Vergi matrahı",
            accounts=sorted({row["raw_code"] for row in kkeg_rows}),
            amount=sum(_expense_row_amount(row) for row in kkeg_rows),
            basis="KVK 11 ve giderin niteliğine ilişkin özel hükümler",
            action="Beyanname KKEG toplamı ile mizan alt hesaplarını mutabık hale getirin.",
        )

    penalty_rows = matching_rows(
        r"CEZA|USULSÜZLÜK|GECİKME\s+(?:ZAMMI|FAİZİ)|TRAFİK|VERGİ\s+ZİYAI"
    )
    if penalty_rows:
        add_check(
            "penalty_expenses",
            "Ceza ve gecikme kalemleri",
            "warning",
            "Açıklaması ceza veya gecikme ödemesine işaret eden gider satırları bulundu.",
            category="Vergi matrahı",
            accounts=sorted({row["raw_code"] for row in penalty_rows}),
            amount=sum(_expense_row_amount(row) for row in penalty_rows),
            basis="KVK 11/1-d",
            action="Vergi, para cezası, gecikme zammı ve faizlerini indirilebilirlik yönünden tek tek kontrol edin.",
        )

    donation_rows = matching_rows(r"BAĞIŞ|YARDIM|SPONSORLUK")
    if donation_rows:
        add_check(
            "donation_expenses",
            "Bağış, yardım ve sponsorluk",
            "info",
            "Bağış, yardım veya sponsorluk ifadesi bulunan gider satırları tespit edildi.",
            category="Vergi matrahı",
            accounts=sorted({row["raw_code"] for row in donation_rows}),
            amount=sum(_expense_row_amount(row) for row in donation_rows),
            basis="KVK 10",
            action="Belge, yararlanıcı, kazanca bağlı sınır ve beyanname üzerindeki indirim sırasını kontrol edin.",
        )

    vehicle_rows = matching_rows(r"ARAÇ|OTOMOBİL|TAŞIT|AKARYAKIT|KASKO|MOTORLU\s+TAŞIT")
    if vehicle_rows:
        add_check(
            "vehicle_expenses",
            "Araç ve binek otomobil giderleri",
            "info",
            "Araç, yakıt, sigorta veya taşıt ifadesi bulunan gider satırları tespit edildi.",
            category="Gider incelemesi",
            accounts=sorted({row["raw_code"] for row in vehicle_rows}),
            amount=sum(_expense_row_amount(row) for row in vehicle_rows),
            basis="GVK 40, KVK 6 ve ilgili gider kısıtlamaları",
            action="Aracın niteliği, işte kullanımı ve dönem için geçerli gider sınırlarını belge bazında inceleyin.",
        )

    for code, title, detail, status, category, basis, action in (
        (
            "368", "Vadesi geçmiş vergi yükümlülükleri",
            "368 hesap bakiyesi ödeme, tecil ve yapılandırma durumu açısından incelenmelidir.",
            "warning", "Vergi borçları", "VUK ve 6183 sayılı Kanun",
            "Alt hesapları tahakkuk, vade ve ödeme planlarıyla mutabık hale getirin.",
        ),
        (
            "131", "Ortaklardan alacaklar",
            "Ortaklardan alacak bakiyesi ilişkili kişi finansmanına işaret edebilir.",
            "info", "İlişkili taraflar", "KVK 13",
            "Emsal faiz, adat hesabı, sözleşme ve tahsilat hareketlerini kontrol edin.",
        ),
        (
            "331", "Ortaklara borçlar",
            "Ortaklara borç bakiyesi örtülü sermaye ve ilişkili kişi işlemlerinde dikkate alınmalıdır.",
            "info", "İlişkili taraflar", "KVK 12 ve 13",
            "Dönem içindeki en yüksek borcu, dönem başı özsermayeyi, faiz ve kur farkını birlikte inceleyin.",
        ),
    ):
        account = account_map.get(code)
        if account and _account_net_amount(account) > MIZAN_TOLERANCE:
            add_check(
                f"account_{code}", title, status, detail,
                category=category,
                accounts=[code],
                amount=_account_net_amount(account),
                basis=basis,
                action=action,
            )

    reverse_balance_codes = []
    for account in summary_accounts or []:
        code = account["code"]
        if code in NEGATIVE_BILANCO_CODES:
            continue
        if code.startswith(("1", "2")) and account["credit_balance"] > MIZAN_TOLERANCE:
            reverse_balance_codes.append(code)
        elif code.startswith(("3", "4", "5")) and account["debit_balance"] > MIZAN_TOLERANCE:
            reverse_balance_codes.append(code)
    if reverse_balance_codes:
        add_check(
            "reverse_balances",
            "Ters bakiye kontrolü",
            "warning",
            "Normal yönünün tersinde bakiye veren hesaplar tespit edildi.",
            category="Muhasebe kapanışı",
            accounts=sorted(reverse_balance_codes),
            basis="Tek Düzen Hesap Planı hesap işleyişi",
            action="Mahsup, virman, sınıflandırma ve dönem sonu kayıtlarını belge bazında kontrol edin.",
        )

    vat_codes = [code for code in ("190", "191", "391") if code in account_map]
    if vat_codes:
        add_check(
            "vat_accounts",
            "KDV hesapları",
            "info",
            "190, 191 ve 391 hesaplarının bakiyeleri dönem KDV beyannamesiyle birlikte incelenmelidir.",
            category="Beyanname mutabakatı",
            accounts=vat_codes,
            amount=sum(_account_net_amount(account_map[code]) for code in vat_codes),
            basis="KDV Kanunu ve KDV Genel Uygulama Tebliği",
            action="Hesaplanan, indirilecek ve devreden KDV tutarlarını KDV1 beyannamesi ve sonraki dönem devriyle karşılaştırın.",
        )

    tax_provision_codes = [code for code in ("193", "360", "370", "371") if code in account_map]
    if tax_provision_codes:
        add_check(
            "tax_provision_accounts",
            "Vergi karşılığı ve peşin ödenen vergiler",
            "info",
            "Peşin ödenen vergiler, vergi karşılığı ve ödenecek vergilere ilişkin hesaplar bulundu.",
            category="Beyanname mutabakatı",
            accounts=tax_provision_codes,
            amount=sum(_account_net_amount(account_map[code]) for code in tax_provision_codes),
            basis="Kurumlar/geçici vergi tahakkuk ve mahsup kayıtları",
            action="193, 360, 370 ve 371 hesaplarını beyanname, tahakkuk fişi ve ödeme kayıtlarıyla mutabık hale getirin.",
        )

    financing_codes = [code for code in ("660", "661", "780") if code in account_map]
    if financing_codes:
        financing_amount = sum(
            abs(_income_amount(account_map[code]))
            if code.startswith("6") else max(account_map[code].get("debit", 0), 0)
            for code in financing_codes
        )
        foreign_sources = sum(
            max(account.get("credit_balance", 0) - account.get("debit_balance", 0), 0)
            for account in summary_accounts or [] if account["code"].startswith(("3", "4"))
        )
        equity = sum(
            max(account.get("credit_balance", 0) - account.get("debit_balance", 0), 0)
            for account in summary_accounts or [] if account["code"].startswith("5")
        )
        restriction_signal = foreign_sources > equity > 0
        add_check(
            "financing_expenses",
            "Finansman giderleri",
            "warning" if restriction_signal else "info",
            (
                "Yabancı kaynaklar özkaynağı aşıyor; finansman gider kısıtlaması hesabı ayrıca yapılmalıdır."
                if restriction_signal else "Finansman gideri bulunan hesaplar tespit edildi."
            ),
            category="Finansman",
            accounts=financing_codes,
            amount=financing_amount,
            basis="KVK 11/1-i ve 1 Seri No.lu KVK Genel Tebliği 11.13",
            action="Yabancı kaynak-özkaynak karşılaştırmasını, istisna ve mükerrer KKEG kalemlerini dikkate alarak hesaplayın.",
        )

    doubtful_codes = [code for code in ("128", "129") if code in account_map]
    if doubtful_codes:
        receivable = _account_net_amount(account_map.get("128", {}))
        provision = _account_net_amount(account_map.get("129", {}))
        add_check(
            "doubtful_receivables",
            "Şüpheli ticari alacaklar",
            "warning" if receivable > MIZAN_TOLERANCE and provision <= MIZAN_TOLERANCE else "info",
            "Şüpheli alacak ve karşılık hesaplarının birlikte değerlendirilmesi gerekir.",
            category="Dönem sonu değerleme",
            accounts=doubtful_codes,
            amount=receivable,
            basis="VUK 323",
            action="Dava/icra takibi, yazılı istem, teminat ve karşılık ayırma şartlarını alacak bazında kontrol edin.",
        )

    fixed_asset_codes = [code for code in ("250", "251", "252", "253", "254", "255", "256", "258") if code in account_map]
    if fixed_asset_codes:
        fixed_asset_amount = sum(_account_net_amount(account_map[code]) for code in fixed_asset_codes)
        depreciation_amount = _account_net_amount(account_map.get("257", {}))
        add_check(
            "fixed_asset_depreciation",
            "Maddi duran varlıklar ve amortisman",
            "warning" if fixed_asset_amount > MIZAN_TOLERANCE and depreciation_amount <= MIZAN_TOLERANCE else "info",
            "Maddi duran varlık hesapları amortisman ve aktifleştirme yönünden kontrol edilmelidir.",
            category="Dönem sonu değerleme",
            accounts=fixed_asset_codes + (["257"] if "257" in account_map else []),
            amount=depreciation_amount,
            basis="VUK 313 ve devamı",
            action="Faydalı ömür, aktife giriş tarihi, kıst amortisman ve maliyete eklenen unsurları sabit kıymet listesiyle karşılaştırın.",
        )

    periodisation_codes = [code for code in ("180", "280", "380", "480") if code in account_map]
    if periodisation_codes:
        add_check(
            "periodisation_accounts",
            "Dönemsellik hesapları",
            "info",
            "Gelecek dönemlere ait gider/gelir ve tahakkuk hesaplarında bakiye bulundu.",
            category="Dönem sonu değerleme",
            accounts=periodisation_codes,
            amount=sum(_account_net_amount(account_map[code]) for code in periodisation_codes),
            basis="VUK tahakkuk ve dönemsellik ilkeleri",
            action="Hizmet dönemi, sözleşme ve fatura tarihlerini kontrol ederek ilgili döneme ait tutarları ayırın.",
        )

    valuation_codes = [code for code in ("646", "656") if code in account_map]
    if valuation_codes:
        add_check(
            "foreign_currency_valuation",
            "Kambiyo kârı ve zararı",
            "info",
            "Kambiyo kârı veya zararı hesaplarında hareket bulundu.",
            category="Dönem sonu değerleme",
            accounts=valuation_codes,
            amount=sum(abs(_income_amount(account_map[code])) for code in valuation_codes),
            basis="VUK 280",
            action="Dövizli hesapların değerleme kuru, tarih ve kur farkı kayıtlarını banka/cari hesap listeleriyle karşılaştırın.",
        )

    inflation_codes = [code for code in ("648", "658", "698") if code in account_map]
    if inflation_codes:
        add_check(
            "inflation_adjustment",
            "Enflasyon düzeltmesi hesapları",
            "info",
            "Enflasyon düzeltmesine ilişkin gelir, gider veya düzeltme hesabında hareket bulundu.",
            category="Dönem sonu değerleme",
            accounts=inflation_codes,
            amount=sum(_account_net_amount(account_map[code]) for code in inflation_codes),
            basis="VUK mükerrer 298/A",
            action="Parasal olmayan kıymetler, düzeltme katsayıları ve vergisel etkiyi dönem mevzuatına göre kontrol edin.",
        )

    inventory_codes = [code for code in ("150", "151", "152", "153", "157", "158", "159", "620", "621", "622", "623") if code in account_map]
    if inventory_codes:
        add_check(
            "inventory_cost_flow",
            "Stok ve satışların maliyeti",
            "info",
            "Stok ve satışların maliyeti hesapları birlikte değerlendirilmek üzere tespit edildi.",
            category="Dönem sonu değerleme",
            accounts=inventory_codes,
            basis="VUK 274 ve 275",
            action="Fiilî sayım, maliyet yöntemi, değer düşüklüğü ve maliyet yansıtma kayıtlarını karşılaştırın.",
        )

    return checks


def build_mizan_tax_checks(raw_rows, summary_accounts):
    """Yeni ve daha önce kaydedilmiş mizanlar için kontrolleri yeniden üretir."""
    return _build_tax_checks(_normalise_saved_mizan_rows(raw_rows), summary_accounts or [])


def _normalised_report_label(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^A-Z0-9]+", " ", text.upper()).strip()


def _report_value(rows, labels):
    wanted = {_normalised_report_label(label) for label in labels}
    for row in rows or []:
        description = next(
            (value for key, value in row.items() if _normalised_report_label(key) in {"ACIKLAMA", "HESAP KALEMI"}),
            "",
        )
        if _normalised_report_label(description) not in wanted:
            continue
        for key, value in row.items():
            if _normalised_report_label(key) in {"CARI DONEM", "TUTAR"} and value is not None:
                return float(to_float_turkish(value))
    return None


def build_mizan_report_comparison(reports, parsed):
    """Beyanname tabloları ile aynı dönem mizan özetini karşılaştırır."""
    reports = reports or {}
    if not reports:
        return []

    balance = reports.get("bilanco", {})
    income = reports.get("gelir", {})
    active_rows = balance.get("aktif", [])
    passive_rows = balance.get("pasif", [])
    income_rows = income.get("tablo", [])

    official_active = _report_value(active_rows, ["AKTİF TOPLAMI"])
    if official_active is None:
        current_assets = _report_value(active_rows, ["I. Dönen Varlıklar"])
        noncurrent_assets = _report_value(active_rows, ["II. Duran Varlıklar"])
        if current_assets is not None and noncurrent_assets is not None:
            official_active = current_assets + noncurrent_assets

    official_passive = _report_value(passive_rows, ["PASİF TOPLAMI"])
    if official_passive is None:
        short_debt = _report_value(passive_rows, ["III. Kısa Vadeli Yabancı Kaynaklar"])
        long_debt = _report_value(passive_rows, ["IV. Uzun Vadeli Yabancı Kaynaklar"])
        equity = _report_value(passive_rows, ["V. Öz Kaynaklar"])
        if short_debt is not None and long_debt is not None and equity is not None:
            official_passive = short_debt + long_debt + equity

    summary = parsed.get("summary", {})
    metrics = [
        ("Aktif toplamı", official_active, summary.get("active_total")),
        ("Pasif toplamı", official_passive, summary.get("passive_total")),
        ("Net satışlar", _report_value(income_rows, ["C. Net Satışlar", "Net Satışlar"]), summary.get("net_sales")),
        ("Dönem kârı veya zararı", _report_value(income_rows, ["Dönem Kârı veya Zararı", "Dönem Karı veya Zararı"]), summary.get("period_profit")),
    ]

    comparison = []
    for title, official_value, mizan_value in metrics:
        if official_value is None or mizan_value is None:
            continue
        difference = round(float(mizan_value) - float(official_value), 2)
        comparison.append({
            "title": title,
            "official": float(official_value),
            "mizan": float(mizan_value),
            "difference": difference,
            "status": "success" if abs(difference) <= MIZAN_TOLERANCE else "warning",
        })
    return comparison


def _preview_payload(parsed):
    summary = parsed.get("summary", {})
    return {
        "summary": summary,
        "validation": parsed.get("validation", []),
        "tax_checks": parsed.get("tax_checks", []),
        "detected_period": parsed.get("detected_period", ""),
        "detected_title": parsed.get("detected_title", ""),
        "source_format": parsed.get("source_format", ""),
    }


def parse_mizan_file(file_path):
    extension = os.path.splitext(str(file_path))[1].lower()
    if extension == ".pdf":
        source_rows, metadata = _extract_pdf_rows(file_path)
    elif extension in {".xlsx", ".xls"}:
        source_rows, metadata = _extract_excel_rows(file_path)
    else:
        raise ValueError("Mizan için PDF, XLSX veya XLS dosyası kullanılabilir.")

    raw_rows = _normalize_source_rows(source_rows)
    summary_accounts, hierarchy_summary = _aggregate_main_accounts(raw_rows)
    income, income_summary = _build_income_table(summary_accounts)
    current_period_result = _current_period_result_for_balance(summary_accounts, income_summary)
    active = _build_balance_table(BILANCO_HESAPLARI["AKTİF"], summary_accounts, "AKTİF")
    passive = _build_balance_table(
        BILANCO_HESAPLARI["PASİF"],
        summary_accounts,
        "PASİF",
        current_period_result=current_period_result,
    )
    validation, totals = _build_validation(
        summary_accounts,
        metadata,
        income_summary,
        current_period_result=current_period_result,
    )
    tax_checks = _build_tax_checks(raw_rows, summary_accounts)

    parsed = {
        "aktif": active,
        "pasif": passive,
        "gelir": income,
        "raw_rows": [
            {
                "Hesap Kodu": row["raw_code"],
                "Ana Hesap": row["main_code"],
                "Açıklama": row["description"],
                "Borç": row["debit"],
                "Alacak": row["credit"],
                "Borç Bakiye": row["debit_balance"],
                "Alacak Bakiye": row["credit_balance"],
            }
            for row in raw_rows
        ],
        "main_accounts": summary_accounts,
        "validation": validation,
        "tax_checks": tax_checks,
        "summary": {
            **totals,
            **income_summary,
            **hierarchy_summary,
            "raw_row_count": len(raw_rows),
            "main_account_count": len(summary_accounts),
            "tax_check_count": len(tax_checks),
            "warning_count": sum(1 for item in validation + tax_checks if item.get("status") == "warning"),
        },
        "source_format": metadata.get("source_format", extension.lstrip(".")),
        "detected_period": metadata.get("detected_period", ""),
        "detected_title": metadata.get("detected_title", ""),
        "has_inflation": False,
        "unvan": metadata.get("detected_title") or "Bilinmiyor",
        "donem": metadata.get("detected_period") or "Bilinmiyor",
    }
    parsed["preview"] = _preview_payload(parsed)
    return parsed


def parse_mizan_excel(excel_path):
    """Eski çağrılar için Excel mizan ayrıştırma uyumluluk katmanı."""
    try:
        return parse_mizan_file(excel_path)
    except Exception as exc:
        return {"status": "error", "message": str(exc)}
