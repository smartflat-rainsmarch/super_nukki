# 레이어 재변환 (Sub-Layer Decomposition) 계획서

> 작성일: 2026-04-02

## 기능 설명
레이어 편집에서 특정 레이어를 우클릭 → "레이어 변환하기" → 해당 레이어 이미지를 파이프라인으로 재분석하여 하위 레이어로 분리. 트리(폴더) 구조로 표시.

## 사용자 플로우
```
1. 레이어 목록에서 레이어 우클릭
2. "레이어 변환하기" 선택
3. 로딩 표시 (2~5초)
4. 원본 레이어가 폴더(▶)로 변환
5. 하위 레이어들이 트리로 표시
6. 폴더 클릭으로 펼침/접힘
```

## 트리 구조 예시
```
▼ card_0 [card] 📁
  ├─ background_0 [background]
  ├─ text_0 [text] "Hello"
  └─ icon_0 [icon]
▶ button_1 [button]
  text_2 [text] "Click me"
  background [background]
```

## API
```
POST /api/project/{id}/layer/{layer_id}/decompose
→ { "children": [...], "count": N }
```

## DB 변경
```sql
ALTER TABLE layers ADD COLUMN parent_id VARCHAR(36) REFERENCES layers(id);
```
