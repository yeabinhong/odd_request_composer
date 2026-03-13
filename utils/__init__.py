"""ODD 기반 데이터 요구사항 정의 서비스 유틸리티"""
from .catalog_loader import (
    load_catalog,
    get_super_classes,
    get_classes,
    get_attributes,
    get_all_attributes_flat
)
from .scenario_generator import (
    calculate_combination_count,
    generate_scenario_id,
    generate_scenarios
)

__all__ = [
    'load_catalog',
    'get_super_classes',
    'get_classes',
    'get_attributes',
    'get_all_attributes_flat',
    'calculate_combination_count',
    'generate_scenario_id',
    'generate_scenarios'
]
