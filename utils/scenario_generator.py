"""시나리오 생성 유틸리티"""
import hashlib
import itertools
from typing import Dict, List, Any


def calculate_combination_count(core_selections: Dict[str, List[str]],
                                 extensions: List[Dict]) -> int:
    """예상 조합 수 계산"""
    count = 1

    # Core ODD 선택 값들의 곱
    for attr_key, values in core_selections.items():
        if values:
            count *= len(values)

    # Extension 값들의 곱
    for ext in extensions:
        if ext.get('values'):
            count *= len(ext['values'])

    return count


def generate_scenario_id(attributes: Dict[str, str]) -> str:
    """scenario_id 생성 (해시 기반)"""
    # key 오름차순 정렬 후 직렬화
    sorted_attrs = sorted(attributes.items())
    serialized = "|".join(f"{k}={v}" for k, v in sorted_attrs)

    # SHA-256 해시 생성
    hash_obj = hashlib.sha256(serialized.encode('utf-8'))
    hash_hex = hash_obj.hexdigest()[:8]

    return f"scenario_{hash_hex}"


def generate_scenarios(region_code: str,
                       region_detail: str,
                       core_selections: Dict[str, List[str]],
                       extensions: List[Dict]) -> List[Dict]:
    """
    조건조합(Scenario) 생성

    Args:
        region_code: 선택된 Region 코드
        region_detail: OTH 선택 시 상세 정보
        core_selections: Core ODD 선택 {attribute_key: [value_codes]}
        extensions: Extension 목록 [{category, display_name, key, values}]

    Returns:
        생성된 시나리오 목록
    """
    scenarios = []

    # 조합할 항목들 준비
    combination_items = []
    combination_keys = []

    # Region 추가 (단일 값)
    combination_keys.append('ext.region')
    combination_items.append([region_code])

    # Core ODD 선택 값 추가
    for attr_key, values in core_selections.items():
        if values:
            combination_keys.append(attr_key)
            combination_items.append(values)

    # Extension 값 추가
    for ext in extensions:
        if ext.get('values'):
            combination_keys.append(ext['key'])
            combination_items.append(ext['values'])

    # Cartesian Product 생성
    if not combination_items:
        return []

    for combo in itertools.product(*combination_items):
        attributes = dict(zip(combination_keys, combo))

        # region_detail 추가 (OTH인 경우)
        if region_code == 'OTH' and region_detail:
            attributes['ext.region.detail'] = region_detail

        scenario = {
            'scenario_id': generate_scenario_id(attributes),
            'attributes': attributes,
            'qty': 0,
            'priority': '중간',
            'notes': ''
        }
        scenarios.append(scenario)

    return scenarios
