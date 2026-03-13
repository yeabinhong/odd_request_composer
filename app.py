"""
ODD 기반 데이터 요구사항 정의 서비스
Streamlit 메인 애플리케이션
"""
import streamlit as st
import json
import uuid
import copy
import pandas as pd
from datetime import datetime, date
from pathlib import Path

from utils.catalog_loader import load_catalog, get_all_attributes_flat
from utils.scenario_generator import calculate_combination_count, generate_scenarios
from utils.excel_export import generate_excel

# 페이지 설정
st.set_page_config(
    page_title="ODD 기반 데이터 요구사항 정의",
    page_icon="🚗",
    layout="wide"
)

# Region 옵션 정의
REGION_OPTIONS = {
    "미국": "USA",
    "한국": "KOR",
    "중국": "CHN",
    "일본": "JPN",
    "유럽": "EUR",
    "지역무관": "ANY",
    "그 외": "OTH"
}

PRIORITY_OPTIONS = ["높음", "중간", "낮음"]


def _info_banner(text: str, color: str = "#1f77b4", bg: str = "#EBF5FB"):
    """좌측 컬러 보더 배너 (단계 안내용)"""
    st.markdown(
        f'<div style="border-left:4px solid {color};background:{bg};'
        f'padding:10px 14px;border-radius:4px;margin-bottom:8px;'
        f'font-size:0.9em;line-height:1.6;">{text}</div>',
        unsafe_allow_html=True
    )


def init_session_state():
    """세션 상태 초기화"""
    if 'catalog' not in st.session_state:
        st.session_state.catalog = load_catalog()

    if 'request_info' not in st.session_state:
        st.session_state.request_info = {
            'title': '',
            'description': '',
            'total_frames': 0,
            'due_date': None,
            'requester_name': '',
            'requester_email': '',
            'product': None,
            'scenario': None,
            'scope': [],
        }

    if 'region' not in st.session_state:
        st.session_state.region = {
            'code': None,
            'detail': ''
        }

    if 'core_selections' not in st.session_state:
        st.session_state.core_selections = {}

    if 'extensions' not in st.session_state:
        st.session_state.extensions = []

    if 'scenarios' not in st.session_state:
        st.session_state.scenarios = []

    if 'scenario_groups' not in st.session_state:
        st.session_state.scenario_groups = []

    if 'current_scenario_name' not in st.session_state:
        st.session_state.current_scenario_name = ''

    if 'editing_group_id' not in st.session_state:
        st.session_state.editing_group_id = None

    if 'pending_save_confirm' not in st.session_state:
        st.session_state.pending_save_confirm = False

    if 'features' not in st.session_state:
        st.session_state.features = []

    if 'qty_unit' not in st.session_state:
        st.session_state.qty_unit = 'frame'

    if 'step' not in st.session_state:
        st.session_state.step = 1


def render_request_info():
    """Step 1: Request 기본 정보 입력"""
    st.header("1. Request 기본 정보")
    _info_banner(
        "📋 최종 산출물(Excel · JSON)에 기록되는 요청 기본 정보입니다. "
        "※ 별표(*) 항목은 필수입니다."
    )

    ri = st.session_state.request_info

    ri['title'] = st.text_input(
        "제목 *",
        value=ri['title'],
        max_chars=100,
        placeholder="예: 미국 야간 고속도로 데이터 요청"
    )

    col3, col4 = st.columns(2)
    with col3:
        ri['requester_name'] = st.text_input(
            "요청인 이름 *",
            value=ri['requester_name'],
            placeholder="예: 홍길동"
        )
    with col4:
        ri['requester_email'] = st.text_input(
            "요청인 이메일 *",
            value=ri['requester_email'],
            placeholder="예: gildong@company.com"
        )

    _product_opts = ["FV", "SVC", "Other"]
    _scenario_opts = ["Driving", "Parking", "Other"]
    col5, col6 = st.columns(2)
    with col5:
        _curr_p = ri.get('product')
        ri['product'] = st.selectbox(
            "Product *",
            options=_product_opts,
            index=_product_opts.index(_curr_p) if _curr_p in _product_opts else None,
            placeholder="선택하세요",
            help="FV = Front Vision (전방 카메라)\nSVC = Surround View Camera (주변 카메라)\nOther = 기타 제품"
        )
    with col6:
        _curr_s = ri.get('scenario')
        ri['scenario'] = st.selectbox(
            "Scenario *",
            options=_scenario_opts,
            index=_scenario_opts.index(_curr_s) if _curr_s in _scenario_opts else None,
            placeholder="선택하세요",
            help="선택한 시나리오 타입에 맞는 Core ODD 속성이 우선 표시됩니다.\n예) Driving 선택 → 주행 관련 속성 상단 노출"
        )

    ri['scope'] = st.multiselect(
        "요청 범위 *",
        options=["데이터 취득", "데이터 라벨링"],
        default=ri.get('scope', []),
        help="데이터 취득: 원본 데이터 수집 요청\n데이터 라벨링: 어노테이션 작업 요청\n두 가지 동시 선택 가능"
    )

    if "데이터 라벨링" in ri.get('scope', []):
        st.markdown("**라벨링 Feature** *(필수)*")
        col_fi, col_fb = st.columns([4, 1])
        with col_fi:
            new_feat_req = st.text_input(
                "Feature 이름",
                placeholder="예: 3DP OD, LPSD, 2DP LD",
                label_visibility="collapsed",
                help="라벨링 Feature = 어노테이션 유형\n예) 3DP OD, LPSD (차선·주차선), 2DP LD"
            )
        with col_fb:
            if st.button("➕ 추가", key="req_add_feature_btn"):
                _name = new_feat_req.strip()
                if _name and _name not in st.session_state.features:
                    _add_feature(_name)
                    st.rerun()
                elif _name in st.session_state.features:
                    st.warning(f"'{_name}'은(는) 이미 추가되어 있습니다.")
        if st.session_state.features:
            for _feat in list(st.session_state.features):
                col_chip, col_del = st.columns([6, 1])
                with col_chip:
                    st.markdown(
                        f'<div style="background:#E8D5F5;color:#5C1B8A;padding:4px 14px;'
                        f'border-radius:12px;display:inline-block;font-weight:600;'
                        f'font-size:0.9em;margin:2px 0;">🏷️ {_feat}</div>',
                        unsafe_allow_html=True
                    )
                with col_del:
                    if st.button("✕", key=f"req_del_feat_{_feat}", help=f"'{_feat}' 삭제"):
                        _remove_feature(_feat)
                        st.rerun()
        else:
            st.caption("⚠️ Feature를 1개 이상 추가해주세요.")

    col7, col8 = st.columns(2)
    with col7:
        ri['description'] = st.text_area(
            "설명",
            value=ri['description'],
            placeholder="요청에 대한 상세 설명 (선택사항)"
        )
    with col8:
        ri['due_date'] = st.date_input(
            "희망 완료일 *",
            value=ri['due_date'],
            min_value=date.today()
        )


def render_region_select():
    """Step 2: Region 필수 선택"""
    st.header("2. Region 선택 (필수)")
    _info_banner("🌍 데이터를 수집할 지역을 선택합니다. 이 그룹의 모든 조건조합에 고정값으로 들어갑니다.")

    region_display = st.selectbox(
        "Region *",
        options=list(REGION_OPTIONS.keys()),
        index=None,
        placeholder="Region을 선택하세요",
        key="region_selectbox"
    )

    if region_display:
        st.session_state.region['code'] = REGION_OPTIONS[region_display]

        if st.session_state.region['code'] == 'OTH':
            detail = st.text_input(
                "상세 지역 입력 *",
                value=st.session_state.region['detail'],
                placeholder="예: Southeast Asia"
            )
            st.session_state.region['detail'] = detail


OTHER_LABEL = "기타 (직접 입력)"


def _render_attr_group(attrs_list):
    """attribute 목록을 Super/Class 그룹별 expander로 렌더링"""
    super_classes = {}
    for attr in attrs_list:
        sc = attr['super_class']
        if sc not in super_classes:
            super_classes[sc] = []
        super_classes[sc].append(attr)

    for super_class, attrs in super_classes.items():
        has_selection = any(a['attribute_key'] in st.session_state.core_selections for a in attrs)
        with st.expander(f"📁 {super_class}", expanded=has_selection):
            classes = {}
            for attr in attrs:
                cn = attr['class_name']
                if cn not in classes:
                    classes[cn] = []
                classes[cn].append(attr)

            for class_name, class_attrs in classes.items():
                st.subheader(f"📋 {class_name}")

                for attr in class_attrs:
                    attr_key = attr['attribute_key']
                    attr_label = attr['attribute_label']
                    values = attr['values']
                    is_required = attr.get('required', False)

                    label_display = (
                        f"⭐ {attr_label} ({attr_key})" if is_required
                        else f"{attr_label} ({attr_key})"
                    )

                    value_options = {v['label_kor']: v['value_code'] for v in values}
                    all_options = list(value_options.keys()) + [OTHER_LABEL]

                    selected_labels = st.multiselect(
                        label_display,
                        options=all_options,
                        key=f"core_{attr_key}"
                    )

                    # 기타 버그 수정: session_state에서 먼저 읽어 fallback
                    other_text_saved = st.session_state.get(f"other_{attr_key}", "")
                    if OTHER_LABEL in selected_labels:
                        st.markdown(
                            '<div style="background:#FFF3CD;border-left:4px solid #FF8C00;'
                            'padding:6px 10px;margin:4px 0 2px 0;border-radius:3px;">'
                            '⚠️ <b>기타 값 직접 입력 (필수)</b></div>',
                            unsafe_allow_html=True
                        )
                        other_text = st.text_input(
                            "기타 값",
                            key=f"other_{attr_key}",
                            placeholder="예: light_reflection_extreme",
                            label_visibility="collapsed"
                        )
                        if not other_text:
                            other_text = other_text_saved
                        if not other_text.strip():
                            st.error("기타 값을 반드시 입력해주세요.")
                    else:
                        other_text = other_text_saved

                    selected_codes = []
                    for label in selected_labels:
                        if label == OTHER_LABEL:
                            if other_text.strip():
                                selected_codes.append(f"other:{other_text.strip()}")
                        else:
                            selected_codes.append(value_options[label])

                    if selected_codes:
                        st.session_state.core_selections[attr_key] = selected_codes
                    elif attr_key in st.session_state.core_selections:
                        del st.session_state.core_selections[attr_key]


def render_core_odd_selection():
    """Step 3: Core ODD 선택"""
    st.header("3. Core ODD 선택")
    _info_banner(
        "🎯 ODD의 핵심 조건을 선택합니다. ⭐ 항목은 권장 필수 조건입니다. "
        "각 속성에서 복수 선택이 가능하며, 선택한 값들의 모든 조합이 조건조합 행으로 생성됩니다."
    )
    st.caption("💡 조건이 많을수록 조합 수가 급격히 늘어납니다. 5단계에서 예상 수를 확인하세요.")

    catalog = st.session_state.catalog
    all_attrs = get_all_attributes_flat(catalog)

    selected_scenario = (st.session_state.request_info.get('scenario') or 'Other').lower()

    if selected_scenario == 'other':
        primary_attrs = all_attrs
        secondary_attrs = []
    else:
        primary_attrs = [a for a in all_attrs if a['product_scenario'] in ['common', selected_scenario]]
        secondary_attrs = [a for a in all_attrs if a['product_scenario'] not in ['common', selected_scenario]]

    _render_attr_group(primary_attrs)

    if secondary_attrs:
        with st.expander("기타 ODD 조건 (추가 선택 가능)", expanded=False):
            _render_attr_group(secondary_attrs)


def render_extensions():
    """Step 4: Extension 입력"""
    st.header("4. Extension 입력")
    _info_banner(
        "🔌 Core ODD로 표현할 수 없는 추가 조건을 자유롭게 정의합니다. "
        "Extension도 조건조합 Cartesian Product에 포함됩니다.",
        color="#e67e22", bg="#FEF9E7"
    )

    # 새 Extension 추가
    with st.expander("➕ Extension 추가", expanded=True):
        col1, col2 = st.columns(2)

        EXT_CATEGORY_OPTIONS = {
            "environmental — 환경 특수조건 (sandstorm, 사막 등)": "environmental",
            "target — 타겟 조건 (object, distance, speed, behavior 등)": "target",
            "vehicle — Ego/차량 조건 (ego speed, lane, headlamp 등)": "vehicle",
            "sensor — 센서/카메라 조건 (bokeh, blur, frozen 등)": "sensor",
        }

        with col1:
            category_display = st.selectbox(
                "카테고리",
                options=list(EXT_CATEGORY_OPTIONS.keys()),
                key="new_ext_category",
                help="target: 검출 대상 조건 (물체, 거리, 속도 등)\nvehicle: 자차 조건 (속도, 차선, 전조등 등)\nsensor: 카메라 조건 (bokeh, blur 등)\nenvironmental: 특수 환경 (모래폭풍 등)"
            )
            category = EXT_CATEGORY_OPTIONS[category_display]

        with col2:
            display_name = st.text_input(
                "표시명 (한글)",
                placeholder="예: 날씨, 자차 기동",
                key="new_ext_display"
            )

        values_input = st.text_input(
            "값 목록 (쉼표로 구분)",
            placeholder="예: 맑음, 흐림, 비, 눈",
            key="new_ext_values",
            help="쉼표(,)로 구분하여 입력\n예) 맑음, 흐림, 비, 눈"
        )
        st.caption("💡 Extension이 없어도 Core ODD만으로 시나리오 생성이 가능합니다.")

        if st.button("Extension 추가"):
            if display_name and values_input:
                # Key 생성 규칙: ext.<category>.<slug>
                slug = display_name.lower().replace(' ', '_')
                # 영문/숫자/underscore만 허용
                slug = ''.join(c if c.isalnum() or c == '_' else '_' for c in slug)
                ext_key = f"ext.{category}.{slug}"

                # 중복 체크
                existing_keys = [e['key'] for e in st.session_state.extensions]
                if ext_key in existing_keys:
                    suffix = 2
                    while f"{ext_key}_{suffix}" in existing_keys:
                        suffix += 1
                    ext_key = f"{ext_key}_{suffix}"

                values = [v.strip() for v in values_input.split(',') if v.strip()]

                st.session_state.extensions.append({
                    'category': category,
                    'display_name': display_name,
                    'key': ext_key,
                    'values': values
                })
                st.rerun()

    # 현재 Extension 목록 표시
    if st.session_state.extensions:
        st.subheader("현재 Extension 목록")

        for i, ext in enumerate(st.session_state.extensions):
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                st.write(f"**{ext['display_name']}** ({ext['category']})")
            with col2:
                st.write(f"값: {', '.join(ext['values'])}")
            with col3:
                if st.button("삭제", key=f"del_ext_{i}"):
                    st.session_state.extensions.pop(i)
                    st.rerun()


def render_combination_preview():
    """조합 수 예상 표시"""
    st.header("5. 조합 수 예상")
    _info_banner(
        "🔢 선택한 조건들의 Cartesian Product 결과 수를 미리 확인합니다. "
        "조합 수가 많으면 '최종 조건조합 테이블'의 일괄 설정을 활용하세요."
    )

    count = calculate_combination_count(
        st.session_state.core_selections,
        st.session_state.extensions
    )

    # Region이 선택되면 조합 수는 그대로 (Region은 단일 선택)
    if st.session_state.region['code']:
        st.metric("예상 시나리오 수", count)

        if count > 1000:
            st.warning("⚠️ 조합 수가 1,000개를 초과합니다. 조건을 줄이는 것을 권장합니다.")
        elif count > 100:
            st.info("ℹ️ 조합 수가 100개를 초과합니다.")
    else:
        st.warning("Region을 먼저 선택해주세요.")


def render_scenario_generation():
    """Step 6: Scenario 생성"""
    st.header("6. Scenario 생성")
    _info_banner(
        "⚡ 조건 선택이 완료되었으면 버튼을 눌러 조건조합을 생성합니다. "
        "생성 후 미리보기를 확인하고 이상이 없으면 저장 버튼을 누르세요."
    )

    # 필수 조건 체크
    can_generate = True
    if not st.session_state.request_info['title']:
        st.error("❌ 제목을 입력해주세요.")
        can_generate = False
    if not st.session_state.region['code']:
        st.error("❌ Region을 선택해주세요.")
        can_generate = False
    if st.session_state.region['code'] == 'OTH' and not st.session_state.region['detail']:
        st.error("❌ '그 외' 선택 시 상세 지역을 입력해주세요.")
        can_generate = False
    if not st.session_state.core_selections and not st.session_state.extensions:
        st.error("❌ Core ODD 또는 Extension을 최소 1개 이상 선택해주세요.")
        can_generate = False

    # 기타 (직접 입력) 선택 후 값 미입력 체크
    for key in list(st.session_state.keys()):
        if key.startswith('core_'):
            attr_key = key[5:]
            if OTHER_LABEL in st.session_state.get(key, []):
                if not st.session_state.get(f'other_{attr_key}', '').strip():
                    st.error(f"❌ '{attr_key}' 항목의 기타 값을 입력해주세요.")
                    can_generate = False

    if can_generate:
        if st.button("🚀 Scenario 생성", type="primary"):
            scenarios = generate_scenarios(
                st.session_state.region['code'],
                st.session_state.region['detail'],
                st.session_state.core_selections,
                st.session_state.extensions
            )
            for s in scenarios:
                s['features'] = {feat: 0 for feat in st.session_state.features}
            st.session_state.scenarios = scenarios
            st.success(f"✅ {len(scenarios)}개의 시나리오가 생성되었습니다.")
            st.rerun()


def _build_attr_label_map(catalog):
    """attribute_key → 한글 라벨"""
    return {a['attribute_key']: a['attribute_label'] for a in get_all_attributes_flat(catalog)}


def _build_value_label_map(catalog):
    """attribute_key → {value_code: label_kor}"""
    return {
        a['attribute_key']: {v['value_code']: v.get('label_kor', v['value_code']) for v in a['values']}
        for a in get_all_attributes_flat(catalog)
    }


def _add_feature(name: str):
    """Feature를 전체 조건조합에 추가"""
    st.session_state.features.append(name)
    for g in st.session_state.scenario_groups:
        for combo in g['combinations']:
            combo.setdefault('features', {})[name] = 0
    for s in st.session_state.scenarios:
        s.setdefault('features', {})[name] = 0


def _remove_feature(name: str):
    """Feature를 전체 조건조합에서 제거"""
    if name in st.session_state.features:
        st.session_state.features.remove(name)
    for g in st.session_state.scenario_groups:
        for combo in g['combinations']:
            combo.get('features', {}).pop(name, None)
    for s in st.session_state.scenarios:
        s.get('features', {}).pop(name, None)


def _reset_working_state():
    """현재 작업 중인 시나리오 그룹 상태 초기화"""
    st.session_state.region = {'code': None, 'detail': ''}
    st.session_state.core_selections = {}
    st.session_state.extensions = []
    st.session_state.scenarios = []
    st.session_state.current_scenario_name = ''
    st.session_state.editing_group_id = None
    st.session_state.pending_save_confirm = False
    keys_to_del = [
        k for k in list(st.session_state.keys())
        if k in ('region_selectbox',) or k.startswith('core_') or k.startswith('other_')
    ]
    for k in keys_to_del:
        del st.session_state[k]


def _save_current_group():
    """현재 작업 중인 조건들을 시나리오 그룹으로 저장"""
    group_id = st.session_state.editing_group_id or str(uuid.uuid4())[:8]
    group = {
        'id': group_id,
        'name': st.session_state.current_scenario_name.strip() or f"시나리오 {len(st.session_state.scenario_groups) + 1}",
        'region': copy.deepcopy(st.session_state.region),
        'core_selections': copy.deepcopy(st.session_state.core_selections),
        'extensions': copy.deepcopy(st.session_state.extensions),
        'combinations': copy.deepcopy(st.session_state.scenarios)
    }
    if st.session_state.editing_group_id:
        for i, g in enumerate(st.session_state.scenario_groups):
            if g['id'] == st.session_state.editing_group_id:
                st.session_state.scenario_groups[i] = group
                break
    else:
        st.session_state.scenario_groups.append(group)
        st.session_state.editing_group_id = group_id  # 재저장 시 update로 처리
    st.session_state.pending_save_confirm = True


def _load_group_to_working_state(group_id: str):
    """저장된 시나리오 그룹을 현재 작업 상태로 불러오기"""
    group = next((g for g in st.session_state.scenario_groups if g['id'] == group_id), None)
    if not group:
        return
    st.session_state.region = copy.deepcopy(group['region'])
    st.session_state.core_selections = copy.deepcopy(group['core_selections'])
    st.session_state.extensions = copy.deepcopy(group['extensions'])
    st.session_state.scenarios = copy.deepcopy(group['combinations'])
    st.session_state.current_scenario_name = group['name']
    st.session_state.editing_group_id = group_id

    # Region 위젯 상태 복원
    region_code = group['region']['code']
    if region_code:
        reverse_map = {v: k for k, v in REGION_OPTIONS.items()}
        region_label = reverse_map.get(region_code)
        if region_label:
            st.session_state['region_selectbox'] = region_label

    # Core ODD 위젯 상태 복원 (value_code → 한글 라벨)
    value_label_map = _build_value_label_map(st.session_state.catalog)
    for attr_key, value_codes in group['core_selections'].items():
        kor_labels = []
        other_text = ''
        for vc in value_codes:
            if vc.startswith('other:'):
                kor_labels.append(OTHER_LABEL)
                other_text = vc[6:]
            else:
                kor_labels.append(value_label_map.get(attr_key, {}).get(vc, vc))
        st.session_state[f'core_{attr_key}'] = kor_labels
        if other_text:
            st.session_state[f'other_{attr_key}'] = other_text


def render_scenario_groups_list():
    """저장된 시나리오 그룹 목록 표시"""
    groups = st.session_state.scenario_groups
    if not groups:
        return

    st.header("저장된 시나리오 그룹")

    for group in groups:
        region_code = group['region']['code'] or '-'
        detail = group['region'].get('detail', '')
        region_str = f"{region_code} ({detail})" if detail else region_code
        n_core = len(group['core_selections'])
        n_ext = len(group['extensions'])
        n_combos = len(group['combinations'])
        group_qty = sum(c['qty'] for c in group['combinations'])

        with st.container(border=True):
            col1, col2, col3 = st.columns([7, 1, 1])
            with col1:
                st.markdown(f"**{group['name']}**")
                st.caption(
                    f"📍 {region_str} &nbsp;|&nbsp; "
                    f"Core ODD {n_core}개 &nbsp;|&nbsp; "
                    f"Extension {n_ext}개 &nbsp;|&nbsp; "
                    f"조건조합 {n_combos}개 &nbsp;|&nbsp; "
                    f"Qty {group_qty:,}"
                )
            with col2:
                if st.button("✏️ 수정", key=f"edit_group_{group['id']}", use_container_width=True):
                    _load_group_to_working_state(group['id'])
                    st.rerun()
            with col3:
                if st.button("🗑️ 삭제", key=f"del_group_{group['id']}", use_container_width=True):
                    st.session_state.scenario_groups = [
                        g for g in st.session_state.scenario_groups if g['id'] != group['id']
                    ]
                    st.rerun()

    st.divider()


def render_scenario_group_builder():
    """시나리오 그룹 빌더 (Region → Core ODD → Extension → 생성 → 저장)"""

    # 저장 직후 초기화 확인 다이얼로그
    if st.session_state.get('pending_save_confirm'):
        saved_group = next(
            (g for g in st.session_state.scenario_groups
             if g['id'] == st.session_state.editing_group_id),
            None
        )
        group_name = saved_group['name'] if saved_group else '시나리오 그룹'
        n_combos = len(saved_group['combinations']) if saved_group else 0
        st.header("저장 완료 ✅")
        st.success(f"**'{group_name}'** 저장 완료 — 조건조합 {n_combos}개")
        st.info("다음 시나리오 그룹을 추가하시겠습니까?\n(아니오를 선택하면 현재 조건을 계속 수정할 수 있습니다.)")
        col_yes, col_no = st.columns(2)
        with col_yes:
            if st.button("➕ 다음 시나리오 그룹 추가", type="primary", use_container_width=True):
                _reset_working_state()
                st.rerun()
        with col_no:
            if st.button("✏️ 현재 그룹 계속 수정", type="secondary", use_container_width=True):
                st.session_state.pending_save_confirm = False
                st.rerun()
        return

    is_editing = st.session_state.editing_group_id is not None
    header = "✏️ 시나리오 그룹 수정 중" if is_editing else "➕ 시나리오 그룹 추가"
    st.header(header)

    current_name = st.text_input(
        "시나리오 이름 *",
        value=st.session_state.current_scenario_name,
        placeholder="예: 야간 주차장, 우천 야간 고속도로"
    )
    st.session_state.current_scenario_name = current_name

    st.divider()
    render_region_select()
    st.divider()
    render_core_odd_selection()
    st.divider()
    render_extensions()
    st.divider()
    render_combination_preview()
    st.divider()
    render_scenario_generation()
    st.divider()
    render_scenario_table()
    st.divider()

    # 저장 / 초기화 버튼
    if not st.session_state.scenarios:
        st.caption("💡 6단계에서 Scenario를 생성한 후 저장할 수 있습니다.")
    col1, col2 = st.columns(2)
    with col1:
        save_label = "✅ 시나리오 수정 완료" if is_editing else "✅ 이 시나리오 저장"
        if st.button(save_label, type="primary", disabled=not st.session_state.scenarios,
                     use_container_width=True):
            if not st.session_state.current_scenario_name.strip():
                st.error("시나리오 이름을 입력해주세요.")
            else:
                _save_current_group()
                st.rerun()
    with col2:
        if st.button("🔄 초기화", type="secondary", use_container_width=True):
            _reset_working_state()
            st.rerun()


def render_scenario_table():
    """Step 7: 생성된 조건조합 미리보기 (읽기 전용)"""
    if not st.session_state.scenarios:
        return

    st.header("7. 생성된 조건조합 미리보기")
    st.info(
        f"✅ {len(st.session_state.scenarios)}개의 조건조합이 생성되었습니다."
    )
    st.caption("💡 수량·우선순위는 이 단계에서 입력하지 않습니다. 모든 그룹 저장 후 '최종 조건조합 테이블'에서 일괄 입력합니다.")

    catalog = st.session_state.catalog
    attr_label_map = _build_attr_label_map(catalog)
    value_label_map = _build_value_label_map(catalog)
    ext_label_map = {ext['key']: ext['display_name'] for ext in st.session_state.extensions}
    ext_label_map['ext.region'] = '지역'

    rows = []
    for idx, s in enumerate(st.session_state.scenarios, start=1):
        row = {'No': idx}
        for k, v in s['attributes'].items():
            col_label = attr_label_map.get(k) or ext_label_map.get(k) or k
            if isinstance(v, str) and v.startswith('other:'):
                display_val = f"[기타] {v[6:]}"
            else:
                display_val = value_label_map.get(k, {}).get(v, v)
            row[col_label] = display_val
        rows.append(row)

    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)


def render_final_combined_table():
    """최종 통합 조건조합 테이블 - 수량/우선순위/Feature 일괄 입력"""
    groups = st.session_state.scenario_groups
    if not groups or not any(g['combinations'] for g in groups):
        return

    st.header("최종 조건조합 테이블")
    _info_banner(
        "📊 모든 시나리오 그룹의 조건조합이 통합 표시됩니다. "
        "수량·우선순위·메모를 입력한 후 반드시 <b>💾 수량/우선순위 저장</b> 버튼을 눌러야 반영됩니다.",
        color="#27ae60", bg="#EAFAF1"
    )
    features = st.session_state.features

    qty_unit = st.radio(
        "수량 단위",
        options=["frame", "hour", "case"],
        horizontal=True,
        key="qty_unit",
        help="frame: Feature별 프레임 수 입력 (라벨링)\nhour: 시간 단위 수량\ncase: 케이스(사례) 단위 수량"
    )
    # frame 단위 + feature 있을 때: feature 열을 수량으로 사용
    use_features = (qty_unit == 'frame') and bool(features)

    tab1, tab2 = st.tabs(["📋 조건조합 테이블", "🔌 Extension 속성"])

    with tab1:
        st.caption("수량/우선순위 입력 후 **'💾 수량/우선순위 저장'** 버튼을 눌러 반영하세요.")

        if qty_unit == 'frame' and not features:
            st.info("ℹ️ frame 단위 수량 입력을 위해 Request 기본 정보에서 '데이터 라벨링'을 선택하고 Feature를 추가하세요.")

        # 일괄 설정
        with st.expander("⚡ 일괄 설정 — 모든 조건조합에 동일한 값을 한 번에 적용"):
            if use_features:
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    bulk_priority = st.selectbox("일괄 우선순위", PRIORITY_OPTIONS, key="final_bulk_priority")
                with col_b2:
                    st.write("")
                    st.write("")
                    if st.button("일괄 우선순위 적용", key="final_bulk_apply"):
                        for g in groups:
                            for combo in g['combinations']:
                                combo['priority'] = bulk_priority
                        st.rerun()
            else:
                col1, col2, col3 = st.columns(3)
                with col1:
                    bulk_qty = st.number_input(
                        "일괄 Qty", min_value=0, value=0, step=100, key="final_bulk_qty"
                    )
                with col2:
                    bulk_priority = st.selectbox("일괄 우선순위", PRIORITY_OPTIONS, key="final_bulk_priority")
                with col3:
                    st.write("")
                    st.write("")
                    if st.button("일괄 적용", key="final_bulk_apply"):
                        for g in groups:
                            for combo in g['combinations']:
                                combo['qty'] = int(bulk_qty)
                                combo['priority'] = bulk_priority
                        st.rerun()

        # 라벨 맵 구성
        catalog = st.session_state.catalog
        attr_label_map = _build_attr_label_map(catalog)
        value_label_map = _build_value_label_map(catalog)
        ext_label_map = {'ext.region': '지역'}
        for g in groups:
            for ext in g['extensions']:
                ext_label_map[ext['key']] = ext['display_name']

        # 속성 열 순서를 먼저 수집 (그룹별 extension 차이로 pandas가 열 순서를 뒤섞는 문제 방지)
        _id_and_edit = {'No', '시나리오 그룹', '시나리오 ID', '수량', '우선순위', '메모'} | {f'feat:{f}' for f in features}
        attr_col_order = []
        _seen_attr = set()
        for g in groups:
            for combo in g['combinations']:
                for k in combo['attributes'].keys():
                    lbl = attr_label_map.get(k) or ext_label_map.get(k) or k
                    if lbl not in _seen_attr and lbl not in _id_and_edit:
                        attr_col_order.append(lbl)
                        _seen_attr.add(lbl)

        # DataFrame 구성
        rows = []
        global_no = 1
        for g in groups:
            for combo in g['combinations']:
                row = {
                    'No': global_no,
                    '시나리오 그룹': g['name'],
                    '시나리오 ID': combo['scenario_id'],
                }
                for k, v in combo['attributes'].items():
                    col_label = attr_label_map.get(k) or ext_label_map.get(k) or k
                    if isinstance(v, str) and v.startswith('other:'):
                        display_val = f"[기타] {v[6:]}"
                    else:
                        display_val = value_label_map.get(k, {}).get(v, v)
                    row[col_label] = display_val
                if use_features:
                    for feat in features:
                        row[f'feat:{feat}'] = combo.get('features', {}).get(feat, 0)
                else:
                    row['수량'] = combo['qty']
                row['우선순위'] = combo['priority']
                row['메모'] = combo.get('notes', '')
                rows.append(row)
                global_no += 1

        df = pd.DataFrame(rows)

        attr_cols = [c for c in attr_col_order if c in df.columns]
        if use_features:
            column_config = {
                'No': st.column_config.NumberColumn("No", disabled=True, width="small"),
                '시나리오 그룹': st.column_config.TextColumn("시나리오 그룹", disabled=True, width="medium"),
                '시나리오 ID': st.column_config.TextColumn("시나리오 ID", disabled=True, width="medium"),
                **{c: st.column_config.TextColumn(c, disabled=True) for c in attr_cols},
                **{f'feat:{feat}': st.column_config.NumberColumn(f"{feat} (frame)", min_value=0, step=100)
                   for feat in features},
                '우선순위': st.column_config.SelectboxColumn("우선순위", options=PRIORITY_OPTIONS, width="small"),
                '메모': st.column_config.TextColumn("메모"),
            }
        else:
            column_config = {
                'No': st.column_config.NumberColumn("No", disabled=True, width="small"),
                '시나리오 그룹': st.column_config.TextColumn("시나리오 그룹", disabled=True, width="medium"),
                '시나리오 ID': st.column_config.TextColumn("시나리오 ID", disabled=True, width="medium"),
                **{c: st.column_config.TextColumn(c, disabled=True) for c in attr_cols},
                '수량': st.column_config.NumberColumn(f"수량 ({qty_unit})", min_value=0, step=100, width="small"),
                '우선순위': st.column_config.SelectboxColumn("우선순위", options=PRIORITY_OPTIONS, width="small"),
                '메모': st.column_config.TextColumn("메모"),
            }

        # 열 순서: No | 시나리오 그룹 | 시나리오 ID | [속성] | [feature/수량] | 우선순위 | 메모
        if use_features:
            editable_ordered = [f'feat:{feat}' for feat in features] + ['우선순위', '메모']
        else:
            editable_ordered = ['수량', '우선순위', '메모']
        column_order = (
            ['No', '시나리오 그룹', '시나리오 ID']
            + [c for c in attr_col_order if c in df.columns]
            + [c for c in editable_ordered if c in df.columns]
        )

        editor_key = f"final_combo_editor_{qty_unit}_{'|'.join(features)}"
        edited_df = st.data_editor(
            df, column_config=column_config, hide_index=True,
            use_container_width=True, key=editor_key, column_order=column_order
        )

        col_save, _ = st.columns([2, 3])
        with col_save:
            if st.button("💾 수량/우선순위 저장", type="primary", use_container_width=True):
                row_idx = 0
                for g in groups:
                    for combo in g['combinations']:
                        row_data = edited_df.iloc[row_idx]
                        if use_features:
                            combo.setdefault('features', {})
                            for feat in features:
                                feat_col = f'feat:{feat}'
                                if feat_col in edited_df.columns:
                                    raw_f = row_data[feat_col]
                                    combo['features'][feat] = int(raw_f) if pd.notna(raw_f) else 0
                        else:
                            raw_qty = row_data['수량']
                            combo['qty'] = int(raw_qty) if pd.notna(raw_qty) else 0
                        raw_pri = row_data['우선순위']
                        combo['priority'] = raw_pri if (pd.notna(raw_pri) and raw_pri in PRIORITY_OPTIONS) else PRIORITY_OPTIONS[1]
                        raw_notes = row_data['메모']
                        combo['notes'] = str(raw_notes) if pd.notna(raw_notes) else ''
                        row_idx += 1
                st.rerun()

        # 메트릭
        total_combos = sum(len(g['combinations']) for g in groups)
        st.metric("총 조건조합 수", total_combos)
        if use_features:
            n_cols = min(len(features), 4)
            feat_metric_cols = st.columns(n_cols)
            for i, feat in enumerate(features):
                feat_total = sum(
                    combo.get('features', {}).get(feat, 0)
                    for g in groups for combo in g['combinations']
                )
                with feat_metric_cols[i % n_cols]:
                    st.metric(feat, f"{feat_total:,} frame")
        else:
            total_qty = sum(sum(c['qty'] for c in g['combinations']) for g in groups)
            st.metric(f"총 Qty ({qty_unit}, 저장 기준)", f"{total_qty:,}")

    with tab2:
        st.subheader("Extension 속성 목록")
        has_any_ext = any(g['extensions'] for g in groups)
        if not has_any_ext:
            st.info("등록된 Extension이 없습니다.")
        else:
            for g in groups:
                if not g['extensions']:
                    continue
                st.markdown(f"#### 📁 {g['name']}")
                ext_rows = []
                for ext in g['extensions']:
                    ext_rows.append({
                        '표시명': ext['display_name'],
                        '키': ext['key'],
                        '카테고리': ext['category'],
                        '값 목록': ', '.join(ext['values'])
                    })
                st.dataframe(pd.DataFrame(ext_rows), hide_index=True, use_container_width=True)
                st.write("")


def render_submit():
    """Submit 및 저장"""
    groups = st.session_state.scenario_groups
    if not groups:
        return

    st.header("Submit")
    _info_banner(
        "🚀 모든 정보를 확인하고 요청서를 저장합니다. 저장 후 Excel · JSON 파일로 다운로드할 수 있습니다.",
        color="#8e44ad", bg="#F5EEF8"
    )

    _qty_unit = st.session_state.get('qty_unit', 'frame')
    _features = st.session_state.get('features', [])
    _use_features = (_qty_unit == 'frame') and bool(_features)

    if _use_features:
        total_qty = sum(
            combo.get('features', {}).get(feat, 0)
            for g in groups for combo in g['combinations'] for feat in _features
        )
    else:
        total_qty = sum(sum(c['qty'] for c in g['combinations']) for g in groups)

    # 필수 입력 검증
    ri_check = st.session_state.request_info
    req_errors = []
    if not ri_check.get('requester_name', '').strip():
        req_errors.append("요청인 이름을 입력해주세요.")
    if not ri_check.get('requester_email', '').strip():
        req_errors.append("요청인 이메일을 입력해주세요.")
    if not ri_check.get('product'):
        req_errors.append("Product를 선택해주세요.")
    if not ri_check.get('scenario'):
        req_errors.append("Scenario를 선택해주세요.")
    if not ri_check.get('scope'):
        req_errors.append("요청 범위를 선택해주세요.")
    if not ri_check.get('due_date'):
        req_errors.append("희망 완료일을 입력해주세요.")
    if "데이터 라벨링" in ri_check.get('scope', []) and not _features:
        req_errors.append("데이터 라벨링 Feature를 1개 이상 추가해주세요.")
    for e in req_errors:
        st.error(f"❌ {e}")

    warnings = []
    if _use_features:
        for g in groups:
            for i, c in enumerate(g['combinations']):
                if all(c.get('features', {}).get(feat, 0) == 0 for feat in _features):
                    warnings.append(f"[{g['name']}] 조건조합 #{i+1}: 모든 Feature 수량이 0입니다.")
    else:
        for g in groups:
            for i, c in enumerate(g['combinations']):
                if c['qty'] == 0:
                    warnings.append(f"[{g['name']}] 조건조합 #{i+1}: Qty가 0입니다.")

    if warnings:
        for w in warnings:
            st.warning(w)

    # 요약 메트릭
    total_combos_submit = sum(len(g['combinations']) for g in groups)
    col_sm1, col_sm2, col_sm3 = st.columns(3)
    with col_sm1:
        st.metric("시나리오 그룹", f"{len(groups)}개")
    with col_sm2:
        st.metric("총 조건조합", f"{total_combos_submit:,}개")
    with col_sm3:
        st.metric(f"총 Qty ({_qty_unit})", f"{total_qty:,}")

    if st.button("💾 JSON으로 저장", type="primary", disabled=bool(req_errors)):
        request_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()
        ri = st.session_state.request_info

        # 그룹별 JSON 구성
        scenario_groups_json = []
        for g in groups:
            selection_json = {
                "region": {
                    "code": g['region']['code'],
                    "detail": g['region']['detail'] or None
                },
                "core": g['core_selections'],
                "extensions": {
                    "ext.region": {
                        "category": "region",
                        "region_code": g['region']['code'],
                        "region_detail": g['region']['detail'] or None
                    }
                }
            }
            for ext in g['extensions']:
                selection_json['extensions'][ext['key']] = {
                    "category": ext['category'],
                    "display_name": ext['display_name'],
                    "values": ext['values']
                }
            scenario_groups_json.append({
                "id": g['id'],
                "name": g['name'],
                "selection": selection_json,
                "combinations": g['combinations']
            })

        total_combos = sum(len(g['combinations']) for g in groups)
        output_data = {
            "request": {
                "id": request_id,
                "title": ri['title'],
                "description": ri['description'],
                "requester": {
                    "name": ri.get('requester_name', ''),
                    "email": ri.get('requester_email', '')
                },
                "product": ri.get('product', ''),
                "scenario": ri.get('scenario', ''),
                "scope": ri.get('scope', []),
                "total_frames": total_qty,
                "due_date": ri['due_date'].isoformat() if ri['due_date'] else None,
                "catalog_version": st.session_state.catalog.get('version', 'unknown'),
                "created_at": now
            },
            "scenario_groups": scenario_groups_json,
            "summary": {
                "total_groups": len(groups),
                "total_combinations": total_combos,
                "total_qty": total_qty,
                "qty_unit": st.session_state.get('qty_unit', 'frame')
            }
        }

        output_dir = Path(__file__).parent / "output"
        output_dir.mkdir(exist_ok=True)
        _safe_title = ri['title'][:40]
        for _ch in r'/\:*?"<>|':
            _safe_title = _safe_title.replace(_ch, '_')
        _safe_title = _safe_title.replace(' ', '_').strip('_') or request_id
        filename = f"request_{_safe_title}_{now[:10]}.json"
        output_path = output_dir / filename

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

        st.success(f"✅ 저장 완료: {output_path}")

        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            excel_buf = generate_excel(output_data, st.session_state.catalog)
            st.download_button(
                label="📊 Excel 다운로드",
                data=excel_buf,
                file_name=filename.replace(".json", ".xlsx"),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=True
            )
        with col_dl2:
            st.download_button(
                label="📄 JSON 다운로드",
                data=json.dumps(output_data, ensure_ascii=False, indent=2),
                file_name=filename,
                mime="application/json",
                use_container_width=True
            )

        with st.expander("📄 생성된 JSON 보기"):
            st.json(output_data)


def main():
    """메인 함수"""
    st.title("🚗 ODD 기반 데이터 요구사항 정의 서비스")
    st.caption("v2.0 - 멀티 시나리오 그룹 지원")

    # 전체 흐름 안내
    st.markdown(
        '<div style="background:#f0f4ff;border:1px solid #c5d3f7;border-radius:8px;'
        'padding:14px 18px;margin-bottom:16px;font-size:0.88rem;line-height:1.8;">'
        '<b style="color:#1a3a8f;">📌 사용 흐름</b><br>'
        '<span style="background:#1a3a8f;color:#fff;border-radius:20px;padding:2px 10px;font-size:0.82rem;font-weight:600;">① 기본 정보 입력</span>'
        ' → '
        '<span style="background:#1a3a8f;color:#fff;border-radius:20px;padding:2px 10px;font-size:0.82rem;font-weight:600;">② 시나리오 그룹 추가 × N</span>'
        ' → '
        '<span style="background:#1a3a8f;color:#fff;border-radius:20px;padding:2px 10px;font-size:0.82rem;font-weight:600;">③ 수량 입력</span>'
        ' → '
        '<span style="background:#1a3a8f;color:#fff;border-radius:20px;padding:2px 10px;font-size:0.82rem;font-weight:600;">④ Submit</span>'
        '<br><span style="font-size:0.82rem;color:#495057;">'
        '시나리오 그룹 = <b>Region 선택 → Core ODD 선택 → Extension 입력 → Scenario 생성 → 저장</b> &nbsp;|&nbsp; '
        '성격이 다른 조건 묶음이 여러 개라면 ② 단계를 반복하세요.</span>'
        '</div>',
        unsafe_allow_html=True
    )

    init_session_state()

    with st.sidebar:
        st.header("📋 진행 상태")
        groups = st.session_state.scenario_groups
        ri_sb = st.session_state.request_info
        features_sb = st.session_state.get('features', [])
        _qty_unit_sb = st.session_state.get('qty_unit', 'frame')
        _use_feat_sb = (_qty_unit_sb == 'frame') and bool(features_sb)

        total_combos = sum(len(g['combinations']) for g in groups)
        if _use_feat_sb:
            total_qty = sum(
                combo.get('features', {}).get(feat, 0)
                for g in groups for combo in g['combinations'] for feat in features_sb
            )
        else:
            total_qty = sum(sum(c['qty'] for c in g['combinations']) for g in groups)

        # Step 1 체크
        info_done = bool(
            ri_sb.get('title', '').strip()
            and ri_sb.get('requester_name', '').strip()
            and ri_sb.get('requester_email', '').strip()
            and ri_sb.get('product')
            and ri_sb.get('scenario')
            and ri_sb.get('scope')
            and ri_sb.get('due_date')
        )
        group_done = len(groups) > 0
        qty_done = total_qty > 0

        st.markdown(f"{'✅' if info_done else '🔲'} **기본 정보**")
        if not info_done:
            missing = []
            if not ri_sb.get('title', '').strip(): missing.append('제목')
            if not ri_sb.get('requester_name', '').strip(): missing.append('요청인 이름')
            if not ri_sb.get('requester_email', '').strip(): missing.append('이메일')
            if not ri_sb.get('product'): missing.append('Product')
            if not ri_sb.get('scenario'): missing.append('Scenario')
            if not ri_sb.get('scope'): missing.append('요청 범위')
            if not ri_sb.get('due_date'): missing.append('희망 완료일')
            st.caption(f"미입력: {', '.join(missing)}")

        st.markdown(f"{'✅' if group_done else '🔲'} **시나리오 그룹** ({len(groups)}개)")
        if group_done:
            st.caption(f"&nbsp;&nbsp;&nbsp;조건조합 {total_combos}개")

        st.markdown(f"{'✅' if qty_done else '🔲'} **수량 입력**")
        if qty_done:
            st.caption(f"&nbsp;&nbsp;&nbsp;총 {total_qty:,} {_qty_unit_sb}")

        if features_sb:
            st.divider()
            st.caption("📌 Feature 목록")
            for f in features_sb:
                st.caption(f"&nbsp;&nbsp;• {f}")

        st.divider()
        if not info_done:
            st.info("👉 기본 정보를 먼저 입력해주세요.")
        elif not group_done:
            st.info("👉 시나리오 그룹을 추가해주세요.")
        elif not qty_done:
            st.info("👉 최종 조건조합 테이블에서 수량을 입력하세요.")
        else:
            st.success("✅ 모든 정보 입력 완료!\nSubmit에서 저장하세요.")

        st.divider()
        if st.button("🔄 새로 시작", type="secondary"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    render_request_info()
    st.divider()

    render_scenario_groups_list()
    render_scenario_group_builder()
    st.divider()

    render_final_combined_table()
    st.divider()

    render_submit()


if __name__ == "__main__":
    main()
