"""
odd_catalog.json 보강 스크립트

odd_class_info_total_req_v1.xlsx v2.7 시트에서
attribute별 한글 라벨, Product_Scenario, Required를 추출하여
data/odd_catalog.json에 추가 필드로 저장한다.

컬럼 (0-indexed):
  4  (E): Attribute key
  12 (M): Attribute_KOR  — 한글 attribute 라벨
  13 (N): Product_Scenario (common / driving / parking)
  14 (O): Required (True / False)
"""
import json
from pathlib import Path

import openpyxl

BASE_DIR = Path(__file__).parent.parent
EXCEL_PATH = BASE_DIR / "odd_class_info_total_req_v1.xlsx"
CATALOG_PATH = BASE_DIR / "data" / "odd_catalog.json"
SHEET_NAME = "v2.7"


def parse_excel_metadata() -> dict:
    """Excel에서 attribute 메타데이터 추출 (첫 등장 행 기준)"""
    wb = openpyxl.load_workbook(EXCEL_PATH, read_only=True, data_only=True)
    ws = wb[SHEET_NAME]

    seen = set()
    attr_meta = {}

    for row in ws.iter_rows(min_row=2, values_only=True):
        attr_key = row[4]  # col E
        if not attr_key:
            continue

        attr_key_clean = str(attr_key).strip()
        if attr_key_clean in seen:
            continue

        seen.add(attr_key_clean)

        kor_label = row[12]        # col M: Attribute_KOR
        product_scenario = row[13] # col N: Product_Scenario
        required = row[14]         # col O: Required

        attr_meta[attr_key_clean] = {
            "attribute_label_kor": str(kor_label).strip() if kor_label else "",
            "product_scenario": str(product_scenario).strip().lower() if product_scenario else "common",
            "required": bool(required) if required is not None else False,
        }

    wb.close()
    return attr_meta


def update_catalog(attr_meta: dict):
    """odd_catalog.json의 각 attribute에 메타데이터 추가"""
    with open(CATALOG_PATH, encoding="utf-8") as f:
        catalog = json.load(f)

    updated = 0
    not_found = []

    for super_data in catalog["super_classes"].values():
        for class_data in super_data["classes"].values():
            attrs = class_data["attributes"]
            for attr_key in list(attrs.keys()):
                attr_key_clean = attr_key.strip()
                if attr_key_clean in attr_meta:
                    meta = attr_meta[attr_key_clean]
                    attrs[attr_key]["attribute_label_kor"] = meta["attribute_label_kor"]
                    attrs[attr_key]["product_scenario"] = meta["product_scenario"]
                    attrs[attr_key]["required"] = meta["required"]
                    updated += 1
                else:
                    not_found.append(attr_key_clean)

    with open(CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)

    print(f"Updated: {updated} attributes")
    if not_found:
        print(f"Not found in Excel ({len(not_found)}): {not_found}")
    print(f"Saved to: {CATALOG_PATH}")


if __name__ == "__main__":
    print(f"Reading: {EXCEL_PATH} / sheet: {SHEET_NAME}")
    attr_meta = parse_excel_metadata()
    print(f"Parsed {len(attr_meta)} attributes from Excel")

    # 샘플 출력
    for k, v in list(attr_meta.items())[:3]:
        print(f"  {k!r}: {v}")

    update_catalog(attr_meta)
