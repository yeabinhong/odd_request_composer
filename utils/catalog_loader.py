"""ODD Catalog 로더 유틸리티"""
import json
from pathlib import Path
from typing import Dict, List, Any
import streamlit as st


@st.cache_data
def load_catalog() -> Dict[str, Any]:
    """ODD Catalog JSON 파일 로드"""
    catalog_path = Path(__file__).parent.parent / "data" / "odd_catalog.json"
    with open(catalog_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_super_classes(catalog: Dict) -> List[str]:
    """Super Class 목록 반환"""
    return list(catalog['super_classes'].keys())


def get_classes(catalog: Dict, super_class: str) -> List[str]:
    """특정 Super Class의 Class 목록 반환"""
    if super_class not in catalog['super_classes']:
        return []
    return list(catalog['super_classes'][super_class]['classes'].keys())


def get_attributes(catalog: Dict, super_class: str, class_name: str) -> List[Dict]:
    """특정 Class의 Attribute 목록 반환"""
    if super_class not in catalog['super_classes']:
        return []
    if class_name not in catalog['super_classes'][super_class]['classes']:
        return []

    attrs = catalog['super_classes'][super_class]['classes'][class_name]['attributes']
    return [
        {
            'key': key,
            'label': data['attribute_label_eng'],
            'values': data['values']
        }
        for key, data in attrs.items()
    ]


def get_all_attributes_flat(catalog: Dict) -> List[Dict]:
    """모든 Attribute를 flat list로 반환 (Super/Class 정보 포함)"""
    result = []
    for super_name, super_data in catalog['super_classes'].items():
        for class_name, class_data in super_data['classes'].items():
            for attr_key, attr_data in class_data['attributes'].items():
                result.append({
                    'super_class': super_name,
                    'class_name': class_name,
                    'attribute_key': attr_key,
                    # 한글 라벨 우선, 없으면 영문 fallback
                    'attribute_label': attr_data.get('attribute_label_kor') or attr_data['attribute_label_eng'],
                    'attribute_label_eng': attr_data['attribute_label_eng'],
                    'product_scenario': attr_data.get('product_scenario', 'common'),
                    'required': attr_data.get('required', False),
                    'values': attr_data['values']
                })
    return result
