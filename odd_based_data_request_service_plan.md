# ODD 기반 데이터 요구사항 정의 서비스 기획서 (v2.0)

## 1. 서비스 개요

### 1.1 목적
기존의 자유 서술형 데이터 요구사항(예: "미국 야간 보행자 4만 프레임")을 **ODD 기반의 구조화된 요구사항**으로 전환한다.

이를 통해:
- 알고리즘팀은 ODD를 잘 몰라도 **선택 중심 UI**로 요구사항을 작성할 수 있고
- 운영팀은 **조건조합(Scenario) 단위로 수량·우선순위를 명확히 관리**할 수 있으며
- 데이터 취득/라벨링/분석 downstream과 **key-value 정합성**을 유지한다.

---

### 1.2 핵심 컨셉
- ODD Catalog 기반 선택 UI
- **멀티 시나리오 그룹** 지원 (성격이 다른 조건 묶음을 복수로 등록)
- Region 필수 선택 + Extension 확장 구조
- 조건조합(Scenario) 자동 생성 (Cartesian Product)
- 최종 통합 테이블에서 Qty / Priority 일괄 입력
- UI는 한글 중심, 저장은 key 기반(JSON) + Excel 다운로드

---

## 2. 전체 워크플로우

```
① 기본 정보 입력
    → ② 시나리오 그룹 추가 × N
         [Region 선택 → Core ODD 선택 → Extension 입력 → Scenario 생성 → 그룹 저장]
    → ③ 최종 조건조합 테이블에서 수량/우선순위 입력
    → ④ Submit → JSON 저장 + Excel/JSON 다운로드
```

- 성격이 다른 조건 묶음이 여러 개라면 ② 단계를 반복하여 여러 그룹을 등록한다.
- 삭제/수정 기능 제공 (그룹 단위 수정, 삭제 가능)
- 금지 조합, 조건부 룰은 v1 범위에서 제외한다.

---

## 3. ODD Catalog 설계 (읽기 전용)

### 3.1 출처
- `data/odd_catalog.json` (odd_class_info_total.xlsx로부터 변환)
- 정본 시트(예: `odd_v2.7`) 기준

### 3.2 구조
```
super_classes
  └─ [Super Class 이름]
       └─ classes
            └─ [Class 이름]
                 └─ attributes
                      └─ [attribute_key]
                           ├─ attribute_label_eng
                           ├─ attribute_label_kor    (UI 표시)
                           ├─ product_scenario       (common / driving / parking)
                           ├─ required               (true/false)
                           └─ values[]
                                ├─ value_code        (저장용)
                                └─ label_kor         (UI 표시)
```

### 3.3 원칙
- 사용자는 attribute_label_kor / label_kor 기준으로 선택
- 시스템 저장은 attribute_key / value_code 기준으로 수행
- `product_scenario` 필드를 이용해 선택한 Scenario 타입(Driving/Parking)에 맞는 속성을 상단 노출

---

## 4. Region 설계 (필수, 단일 선택)

### 4.1 Category
- Extension category 중 하나: `region`
- Core ODD에는 포함되지 않음; 시나리오 그룹별로 필수 선택

### 4.2 UI 옵션 (단일 선택)
- 미국
- 한국
- 중국
- 일본
- 유럽 (지리적 유럽)
- 지역무관
- 그 외 (직접 입력)

### 4.3 저장 값 (3글자 코드 고정)

| UI 선택 | 저장 코드 | 비고 |
|--------|----------|------|
| 미국 | USA | ISO |
| 한국 | KOR | ISO |
| 중국 | CHN | ISO |
| 일본 | JPN | ISO |
| 유럽(지리) | EUR | 사내 코드 |
| 지역무관 | ANY | 사내 코드 |
| 그 외 | OTH | 사내 코드 + detail |

- `OTH` 선택 시 `region_detail` 필수 입력

---

## 5. Extension 설계

### 5.1 Extension Categories
고정된 네 가지 카테고리 (UI 선택; region은 별도 필수 선택):

| 카테고리 | 설명 |
|----------|------|
| `environmental` | 환경 특수조건 (sandstorm, 사막, 모래바람 등) |
| `target` | 타겟 관련 조건 (object, distance, speed, behavior, direction 등) |
| `vehicle` | Ego/차량 조건 (ego speed, lane, headlamp 등) |
| `sensor` | 센서/카메라 조건 (bokeh, blur, frozen windscreen, glare 등) |

> **변경 배경 (26YQ1):** 기존 `environmental` / `behavioral` 분류를 target·vehicle·sensor로 세분화함.

### 5.2 입력 방식
- 사용자는 **카테고리 선택 + 표시명(한글) + 값 목록(쉼표 구분)** 입력
- 시스템이 Extension key 자동 생성

#### Key 생성 규칙
```
ext.<category>.<slug>
```
- 소문자
- 공백은 underscore로 치환
- 영문/숫자/underscore만 허용
- 중복 시 `_2`, `_3` suffix 부여

### 5.3 조합 포함 정책
- 모든 Extension은 기본적으로 **combinatorial**
- 값 개수만큼 조합 수 증가

---

## 6. 조건조합(Scenario) 생성 규칙

### 6.1 생성 방식
- 전 조합(Cartesian Product)

### 6.2 조합 대상
```
Region (1개)
× Core ODD 선택값
× 모든 Extension 값
```

### 6.3 예상 조합 수 계산
```
1 (region)
× Π(core attribute별 선택 value 수)
× Π(extension별 value 수)
```

UI에서 실시간 표시 및 임계치 경고 제공:
- 100개 초과: 안내 메시지
- 1,000개 초과: 경고 메시지

---

## 7. 시나리오 그룹 (Multi-Group)

### 7.1 개념
- 하나의 Request에 성격이 다른 조건 묶음을 **복수로 등록** 가능
- 각 그룹은 `Region + Core ODD + Extension + Combinations`로 구성

### 7.2 그룹 저장/관리
- 그룹 저장 시 이름 지정 필수 (예: "야간 주차장", "우천 야간 고속도로")
- 저장된 그룹은 수정(✏️) / 삭제(🗑️) 가능
- 저장 후 새 그룹 추가 여부를 확인하는 다이얼로그 표시

### 7.3 최종 통합 테이블
- 전체 그룹의 조건조합이 단일 테이블로 통합 표시
- **수량 단위** 선택: `frame` / `hour` / `case`
  - `frame` 단위 + Feature 등록 시: Feature별 frame 수 입력 (Feature 열로 qty 대체)
  - `hour` / `case` 단위: qty 단일 열 입력
- **일괄 설정**: 모든 조합에 동일 qty / 우선순위 일괄 적용 가능
- **💾 수량/우선순위 저장** 버튼으로 반영

---

## 8. 우선순위

| UI 표시 | 저장 값 |
|---------|---------|
| 높음 | 높음 |
| 중간 | 중간 |
| 낮음 | 낮음 |

> 기존 계획(P0/P1/P2)에서 한글 표기로 변경 (운영팀 친화성 우선).

---

## (1) UI 필드 명세

### Request Info (Step 1)
| 필드 | 타입 | 필수 | 검증 |
|------|------|------|------|
| title | string | O | 1~100자 |
| requester_name | string | O | - |
| requester_email | string | O | - |
| product | enum | O | FV / SVC / Other |
| scenario | enum | O | Driving / Parking / Other |
| scope | multi-select | O | 데이터 취득 / 데이터 라벨링 |
| description | text | X | - |
| due_date | date | O | 오늘 이후 |
| features | array | 조건부 | scope에 '데이터 라벨링' 포함 시 1개 이상 필수 |

> `total_frames`는 사용자가 직접 입력하지 않으며, 조건조합 qty 합산으로 자동 산출된다.

### Region (시나리오 그룹별)
| 필드 | 타입 | 필수 | 검증 |
|------|------|------|------|
| region_code | enum | O | 단일 선택 |
| region_detail | string | 조건부 | region_code=OTH일 때 필수 |

### Core ODD Selection (시나리오 그룹별)
| 필드 | 타입 | 필수 | 검증 |
|------|------|------|------|
| attribute | multi-select | X | catalog 내 항목만 |
| values | multi-select | X | 최소 1개 (catalog 값 + "기타 (직접 입력)" 선택 가능) |
| other_value | string | 조건부 | values에 "기타 (직접 입력)" 포함 시 필수, 1~100자 |

> **"기타 (직접 입력)" 옵션:** `allow_other: true`로 설정된 attribute에 한해 제공.
> 저장 형식: `["value_code", "other:<입력값>"]`
> 예시: `da_road_surface_condition: ["light_reflection_yes", "other:light_reflection_extreme"]`
>
> **적용 배경 (26YQ1):** ODD catalog에 정확한 value가 없어 Pre-meta로 임시 처리되던 항목들을 서비스 내에서 직접 기입 가능하도록 함.

### Extension (시나리오 그룹별)
| 필드 | 타입 | 필수 | 검증 |
|------|------|------|------|
| category | enum | O | environmental / target / vehicle / sensor |
| display_name | string | O | 1~50자 |
| values | array | O | 최소 1개 (쉼표 구분 입력) |

### 최종 조건조합 테이블
| 필드 | 타입 | 필수 | 검증 |
|------|------|------|------|
| scenario_id | string | auto | - |
| qty | number | O (frame 아닐 때) | ≥ 0 |
| features | map<string,number> | O (frame 단위 시) | ≥ 0 per feature |
| priority | enum | O | 높음 / 중간 / 낮음 |
| notes | string | X | - |

---

## (2) 저장 JSON 스키마

```json
{
  "request": {
    "id": "string",
    "title": "string",
    "description": "string",
    "requester": {
      "name": "string",
      "email": "string"
    },
    "product": "FV|SVC|Other",
    "scenario": "Driving|Parking|Other",
    "scope": ["데이터 취득", "데이터 라벨링"],
    "total_frames": "number",
    "due_date": "string",
    "catalog_version": "string",
    "created_at": "string"
  },
  "scenario_groups": [
    {
      "id": "string",
      "name": "string",
      "selection": {
        "region": {
          "code": "USA|EUR|KOR|CHN|JPN|ANY|OTH",
          "detail": "string|null"
        },
        "core": {
          "<attribute_key>": ["<value_code>", "other:<custom_text>"]
        },
        "extensions": {
          "ext.region": {
            "category": "region",
            "region_code": "string",
            "region_detail": "string|null"
          },
          "ext.<category>.<slug>": {
            "category": "environmental|target|vehicle|sensor",
            "display_name": "string",
            "values": ["string"]
          }
        }
      },
      "combinations": [
        {
          "scenario_id": "string",
          "attributes": {
            "<key>": "<value>"
          },
          "qty": "number",
          "features": {
            "<feature_name>": "number"
          },
          "priority": "높음|중간|낮음",
          "notes": "string"
        }
      ]
    }
  ],
  "summary": {
    "total_groups": "number",
    "total_combinations": "number",
    "total_qty": "number",
    "qty_unit": "frame|hour|case"
  }
}
```

---

## (3) scenario_id 생성 규칙

### 목적
- 시나리오 동일성 보장
- 입력 순서와 무관한 재현성 확보

### 생성 방식
1. attributes를 key 오름차순 정렬
2. `key=value` 형태로 직렬화
3. `|`로 join
4. SHA-256 해시 생성 (앞 8자리 사용)
5. `scenario_` prefix 부여

### 예시
```
ext.region=USA|
time_from_intensity=night|
weather=rain|
ext.vehicle.ego_speed=highway
```

→ SHA-256 해시 앞 8자리 → `scenario_8f2c1a3b`

---

## (4) 파일 구조

```
ODD_based_req/
├── app.py                    # Streamlit 메인 앱 (v2.0)
├── requirements.txt
├── data/
│   └── odd_catalog.json      # ODD Catalog (읽기 전용)
├── utils/
│   ├── __init__.py
│   ├── catalog_loader.py     # Catalog 로드 & flat list 변환
│   ├── scenario_generator.py # 조합 수 계산 & Scenario 생성
│   └── excel_export.py       # Excel 산출물 생성 (3 시트)
├── scripts/
│   └── enrich_catalog.py     # xlsx → odd_catalog.json 변환 스크립트
└── output/
    └── request_<title>_<date>.json   # 저장된 요청서
```

---

## (5) Excel 산출물 구조

Submit 후 다운로드할 수 있는 Excel 파일은 3개 시트로 구성된다.

| 시트 | 내용 |
|------|------|
| 요청 요약 | Request ID, 제목, 요청인, Product/Scenario, 범위, 완료일, 총 Qty |
| 조건조합 목록 | 핵심 산출물. 전체 그룹의 조건조합 flat 목록 (Region/Core ODD/Extension 열 구분 색상) |
| 선택 요약 | 그룹별 Core ODD 선택 내용 + Extension 선택 내용 (코드 + 한글) |

---

## 부록

본 서비스는:
- Excel/VBA 의존 제거
- Mac/Windows 환경 독립 (Streamlit 웹 앱)
- ODD 확장성 확보
- 알고리즘팀 친화적 UX (선택 중심, 한글 표시)
- 멀티 시나리오 그룹으로 복합 요구사항 표현 가능
- 운영 및 downstream 정합성 (key-value 기반 JSON)

을 목표로 하는 v2.0 완성 설계 문서이다.
