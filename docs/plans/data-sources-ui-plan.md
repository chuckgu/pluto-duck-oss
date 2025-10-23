# Data Sources UI 구현 계획

## 개요
- **목표**: 외부 데이터 소스(CSV, Parquet, PostgreSQL, SQLite)를 관리하고 DuckDB로 임포트하는 직관적인 UI 제공
- **핵심 컨셉**: Data Sources = 외부 원본 연결 정보 + 임포트 기록 관리
- **UX 전략**: 자주 사용하는 선택은 PromptInput 드롭다운으로, 관리는 전용 화면으로

## 아키텍처

### 데이터 플로우
```
외부 소스 (CSV, DB 등)
    ↓ [Import via Connector]
DuckDB 테이블 (로컬 복사본)
    ↓ [Agent Query]
분석 결과
```

### DB 스키마

#### 1. Projects 테이블 (완료)
```sql
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY,
    name VARCHAR NOT NULL,
    description VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    settings JSON,
    is_default BOOLEAN DEFAULT FALSE
);
```

#### 2. Data Sources 테이블 (신규)
```sql
CREATE TABLE IF NOT EXISTS data_sources (
    id UUID PRIMARY KEY,
    project_id UUID,                    -- NULL = 글로벌, 향후 프로젝트별 관리
    
    -- 사용자 친화적 정보
    name VARCHAR NOT NULL,              -- "Customer Data", "Sales Report"
    description VARCHAR,                -- "Monthly customer export from CRM"
    
    -- 외부 소스 연결 정보
    connector_type VARCHAR NOT NULL,    -- "csv", "parquet", "postgres", "sqlite"
    source_config JSON NOT NULL,        -- {"path": "/Users/.../file.csv", "dsn": "postgresql://..."}
    
    -- DuckDB 임포트 정보
    target_table VARCHAR NOT NULL,      -- "customers", "orders"
    rows_count INTEGER,                 -- 임포트된 행 수
    
    -- 상태 관리
    status VARCHAR DEFAULT 'active',    -- "active", "syncing", "error"
    last_imported_at TIMESTAMP,
    error_message VARCHAR,
    
    -- 메타데이터
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSON                       -- 스키마 정보, 샘플 데이터 등
);

CREATE INDEX IF NOT EXISTS idx_sources_project ON data_sources(project_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_sources_table ON data_sources(target_table);
```

#### 3. Conversations.metadata (완료)
```sql
-- 대화별 설정 저장
metadata JSON  -- {"model": "gpt-5", "data_source_id": "uuid"}
```

---

## UI 설계

### 1. 사이드바 네비게이션

#### 레이아웃
```
┌─────────────────────────┐
│              [↻] [+]   │ ← 채팅 액션 (우측 정렬)
├─────────────────────────┤
│ 💬 대화 1               │
│ 💬 대화 2               │
│ 💬 대화 3               │ ← 채팅 목록
│                         │
├─────────────────────────┤
│ [📊] Data Sources      │ ← 데이터 소스 화면 전환
├─────────────────────────┤
│ [⚙️] Settings          │ ← 설정 모달
└─────────────────────────┘
```

#### 버튼 동작
- **💬 대화 클릭**: 채팅 화면으로 전환
- **📊 Data Sources**: 데이터 소스 관리 화면으로 전환
- **⚙️ Settings**: 설정 모달 오픈 (기존)

---

### 2. Data Sources 화면 (메인 영역 전환)

#### 레이아웃
```
┌────────────────────────────────────────────────────┐
│  Data Sources                                      │
│  Manage your external data sources and imports     │
├────────────────────────────────────────────────────┤
│                                                    │
│  Connected Sources                                 │
│  ┌──────────────────────────────────────────────┐ │
│  │ 📄 Customer Data                             │ │
│  │ Source: ~/Documents/data/customers.csv       │ │
│  │ Table: customers  •  1,234 rows              │ │
│  │ Last imported: 2 hours ago                   │ │
│  │                       [Re-import] [Delete]   │ │
│  ├──────────────────────────────────────────────┤ │
│  │ 📦 Sales Report                              │ │
│  │ Source: ~/Documents/data/sales.parquet       │ │
│  │ Table: sales  •  8,901 rows                  │ │
│  │ Last imported: 1 day ago                     │ │
│  │                       [Re-import] [Delete]   │ │
│  ├──────────────────────────────────────────────┤ │
│  │ 🐘 Production Analytics                      │ │
│  │ Source: postgresql://prod.example.com/...    │ │
│  │ Table: analytics  •  12,345 rows             │ │
│  │ Last imported: 3 hours ago                   │ │
│  │                       [Re-import] [Delete]   │ │
│  └──────────────────────────────────────────────┘ │
│                                                    │
│  Import New Data Source                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────┐│
│  │   CSV    │ │  Parquet │ │PostgreSQL│ │SQLite││
│  │    📄    │ │    📦    │ │    🐘    │ │  💾  ││
│  │Click to  │ │  Click   │ │  Click   │ │Click ││
│  │  import  │ │    to    │ │    to    │ │  to  ││
│  └──────────┘ └──────────┘ └──────────┘ └──────┘│
│                                                    │
└────────────────────────────────────────────────────┘
```

#### 각 소스 카드 표시 정보
- **아이콘** + **이름** (사용자 정의)
- **Source**: 원본 위치 (파일 경로, DB 연결 문자열)
- **Table**: DuckDB 테이블명
- **통계**: 행 수, 마지막 임포트 시간
- **액션**: Re-import (재동기화), Delete

---

### 3. Import Modal (카드 클릭 시)

#### CSV/Parquet 임포트
```
┌──────────────────────────────────────┐
│  Import CSV File                  [×]│
├──────────────────────────────────────┤
│                                      │
│  Display Name                        │
│  ┌────────────────────────────────┐ │
│  │ Customer Data                  │ │
│  └────────────────────────────────┘ │
│                                      │
│  File Path                           │
│  ┌────────────────────────────────┐ │
│  │ /Users/.../customers.csv  [📁]│ │
│  └────────────────────────────────┘ │
│                                      │
│  Table Name (in DuckDB)              │
│  ┌────────────────────────────────┐ │
│  │ customers                      │ │ ← 자동 제안
│  └────────────────────────────────┘ │
│                                      │
│  Description (optional)              │
│  ┌────────────────────────────────┐ │
│  │ Monthly customer exports       │ │
│  └────────────────────────────────┘ │
│                                      │
│  ☑ Overwrite if table exists        │
│                                      │
│           [Cancel]  [Import]         │
└──────────────────────────────────────┘
```

#### PostgreSQL/SQLite 임포트
```
┌──────────────────────────────────────┐
│  Import from PostgreSQL           [×]│
├──────────────────────────────────────┤
│  Display Name                        │
│  ┌────────────────────────────────┐ │
│  │ Production Analytics           │ │
│  └────────────────────────────────┘ │
│                                      │
│  Connection String (DSN)             │
│  ┌────────────────────────────────┐ │
│  │ postgresql://user@host/db      │ │
│  └────────────────────────────────┘ │
│  [Test Connection]                   │
│                                      │
│  Query                               │
│  ┌────────────────────────────────┐ │
│  │ SELECT * FROM analytics        │ │
│  │ WHERE date > '2024-01-01'      │ │
│  └────────────────────────────────┘ │
│                                      │
│  Target Table Name                   │
│  ┌────────────────────────────────┐ │
│  │ analytics                      │ │
│  └────────────────────────────────┘ │
│                                      │
│           [Cancel]  [Import]         │
└──────────────────────────────────────┘
```

---

### 4. PromptInput 드롭다운 (통합)

#### 레이아웃
```
┌─────────────────────────────────────────────────┐
│ 메시지 입력...                                   │
├─────────────────────────────────────────────────┤
│ [Data: All ▼] [Model: GPT-5-mini ▼]  [전송]   │
└─────────────────────────────────────────────────┘
```

#### Data 드롭다운 내용
```
┌─────────────────────────────────┐
│ All sources             ✓       │ ← 기본값
├─────────────────────────────────┤
│ customers                       │
│ sales                           │
│ analytics                       │
└─────────────────────────────────┘
```

**특징:**
- 단순하고 깔끔한 목록
- 아이콘, 메타정보 없음
- 순수하게 테이블 이름만 표시
- 추가 관리는 Data Sources 화면에서
- "All sources"로 명명 (Data Sources와 용어 일관성)

---

## 백엔드 API

### 신규 엔드포인트

#### `GET /api/v1/data-sources`
**응답:**
```json
[
  {
    "id": "uuid",
    "name": "Customer Data",
    "description": "Monthly customer exports",
    "connector_type": "csv",
    "source_config": {"path": "/Users/.../customers.csv"},
    "target_table": "customers",
    "rows_count": 1234,
    "status": "active",
    "last_imported_at": "2025-10-22T14:30:00Z",
    "created_at": "2025-10-22T10:00:00Z"
  }
]
```

#### `POST /api/v1/data-sources`
**요청:**
```json
{
  "name": "Customer Data",
  "description": "Monthly customer exports",
  "connector_type": "csv",
  "source_config": {"path": "/Users/.../customers.csv"},
  "target_table": "customers",
  "overwrite": true
}
```

**응답:**
```json
{
  "id": "uuid",
  "status": "active",
  "rows_imported": 1234,
  "message": "Successfully imported 1234 rows"
}
```

#### `POST /api/v1/data-sources/{id}/sync`
외부 소스에서 재임포트

#### `DELETE /api/v1/data-sources/{id}`
소스 삭제 (DuckDB 테이블도 삭제할지 옵션)

---

## 구현 단계

### Phase 1: 백엔드 API (우선)
- [ ] `data_sources` 테이블 스키마 추가
- [ ] DataSourceRepository 생성
  - CRUD 메서드 (create, list, get, delete)
  - sync (재임포트) 메서드
- [ ] `/api/v1/data-sources` 라우터 구현
  - GET (목록), POST (추가), DELETE (삭제)
  - POST /{id}/sync (재동기화)
- [ ] 기존 IngestionService와 통합

### Phase 2: Data Sources 화면
- [ ] `DataSourcesView` 컴포넌트 생성
- [ ] 연결된 소스 목록 표시
  - 이름, 타입, 테이블, 행 수, 마지막 임포트 시간
  - Re-import, Delete 액션
- [ ] 커넥터 카드 그리드 (CSV, Parquet, PostgreSQL, SQLite)
- [ ] 카드 클릭 → Import Modal
- [ ] 사이드바에 "Data Sources" 버튼 추가
- [ ] View 전환 로직 (채팅 ↔ 데이터 소스)

### Phase 3: Import Modals
- [ ] `ImportCSVModal` 컴포넌트
  - 이름, 파일 경로, 테이블명, 설명, overwrite 옵션
- [ ] `ImportParquetModal` (CSV와 유사)
- [ ] `ImportPostgresModal`
  - DSN, Query, Test Connection 버튼
- [ ] `ImportSQLiteModal`
  - 파일 경로, Query

### Phase 4: PromptInput 통합
- [ ] Data Source 선택 드롭다운 추가
  - "All tables" (기본값)
  - 연결된 소스 목록
  - "+ Manage sources..." (Data Sources 화면으로)
- [ ] 선택된 소스를 메시지와 함께 전송
- [ ] Agent가 특정 테이블 우선 사용하도록 컨텍스트 전달

### Phase 5: Agent 통합
- [ ] AgentState에 `preferred_tables` 필드 추가
- [ ] Schema 노드에서 선택된 테이블 우선 표시
- [ ] SQL 노드에서 선택된 테이블 우선 사용

---

## 사용자 워크플로우

### 시나리오 1: 처음 사용자
1. Data Sources 버튼 클릭
2. 화면 전환 → "Connected Sources" 빈 상태 + 카드 보임
3. CSV 카드 클릭
4. 파일 선택, 테이블명 입력
5. Import 클릭
6. 목록에 추가됨
7. 사이드바에서 대화 클릭 → 채팅 화면으로 복귀
8. PromptInput 드롭다운에서 방금 추가한 "customers" 선택
9. "Show top 10 customers" 입력 → 전송
10. Agent가 customers 테이블 우선 사용

### 시나리오 2: 숙련 사용자
1. PromptInput 드롭다운에서 "customers" 선택
2. 질문 입력 → 전송
3. (필요시) Data Sources 화면에서 새 소스 추가

### 시나리오 3: 데이터 동기화
1. Data Sources 화면
2. "Customer Data" 카드에서 "Re-import" 클릭
3. 외부 CSV에서 최신 데이터 재로드
4. "Successfully synced 1,456 rows" 메시지
5. 이후 쿼리는 최신 데이터 사용

---

## 파일 구조

```
backend/pluto_duck_backend/
├── app/
│   ├── api/v1/
│   │   └── data_sources/
│   │       ├── __init__.py
│   │       └── router.py
│   └── services/
│       └── data_sources/
│           ├── __init__.py
│           └── repository.py
└── (기존 ingestion 재사용)

frontend/pluto_duck_frontend/
├── components/
│   └── data-sources/
│       ├── DataSourcesView.tsx
│       ├── SourceCard.tsx
│       ├── ConnectorGrid.tsx
│       ├── ImportCSVModal.tsx
│       ├── ImportParquetModal.tsx
│       ├── ImportPostgresModal.tsx
│       └── ImportSQLiteModal.tsx
├── lib/
│   └── dataSourcesApi.ts
└── app/
    └── page.tsx (view 전환 로직)
```

---

## 기술적 세부사항

### PromptInput 드롭다운 순서
```tsx
<PromptInputFooter>
  <PromptInputTools>
    {/* 1. 데이터 소스 선택 (먼저) */}
    <DataSourceSelect value={selectedSource} onValueChange={setSelectedSource}>
      <DataSourceSelectTrigger>
        <DataSourceSelectValue />
      </DataSourceSelectTrigger>
      <DataSourceSelectContent>
        <DataSourceSelectItem value="all">All sources</DataSourceSelectItem>
        {dataSources.map(source => (
          <DataSourceSelectItem key={source.id} value={source.target_table}>
            {source.target_table}
          </DataSourceSelectItem>
        ))}
      </DataSourceSelectContent>
    </DataSourceSelect>
    
    {/* 2. 모델 선택 (다음) */}
    <PromptInputModelSelect value={selectedModel} onValueChange={setSelectedModel}>
      ...
    </PromptInputModelSelect>
  </PromptInputTools>
  
  <PromptInputSubmit />
</PromptInputFooter>
```

**드롭다운 특징:**
- 단순한 목록 (All tables + 테이블명들)
- 부가 정보 없음 (행 수, 시간 등)
- "+ Manage sources..." 제거 (Data Sources 버튼 사용)
- 모델 드랍다운과 같은 깔끔한 디자인

### View State 관리
```tsx
type ViewMode = 'chat' | 'data-sources';
const [currentView, setCurrentView] = useState<ViewMode>('chat');

// 사이드바 버튼
<button onClick={() => setCurrentView('data-sources')}>
  Data Sources
</button>

// 메인 영역
{currentView === 'chat' && <ChatView />}
{currentView === 'data-sources' && <DataSourcesView />}
```

### 메시지 전송 시 컨텍스트
```tsx
const handleSubmit = async (message: PromptInputMessage) => {
  const metadata = {
    model: selectedModel,
    data_source: selectedSource !== 'all' ? selectedSource : undefined
  };
  
  await createConversation({
    question: message.text,
    model: selectedModel,
    metadata: metadata
  });
};
```

---

## 향후 확장성

### 추가 가능한 커넥터
- **Google Sheets** (OAuth 인증)
- **REST API** (JSON endpoint)
- **S3/GCS** (클라우드 파일)
- **Excel** (.xlsx)

### 고급 기능
- **자동 동기화**: 주기적으로 외부 소스 체크
- **스키마 추적**: 컬럼 변경 감지
- **데이터 프리뷰**: 임포트 전 샘플 표시
- **변환 파이프라인**: 임포트 시 dbt 모델 자동 실행

---

## 체크리스트

### Phase 1: 백엔드
- [ ] `data_sources` 테이블 스키마
- [ ] DataSourceRepository CRUD
- [ ] API 라우터 구현
- [ ] 기존 ingestion과 통합

### Phase 2: UI 기본
- [ ] DataSourcesView 컴포넌트
- [ ] 소스 목록 표시
- [ ] 커넥터 카드 그리드
- [ ] View 전환 로직

### Phase 3: Import 기능
- [ ] CSV/Parquet Import Modal
- [ ] PostgreSQL/SQLite Import Modal
- [ ] Re-import/Delete 액션

### Phase 4: PromptInput 통합
- [ ] 데이터 소스 드롭다운
- [ ] 순서: Model → Data Source
- [ ] 선택된 소스를 메타데이터로 전송

### Phase 5: Agent 최적화
- [ ] 선택된 테이블 우선 사용
- [ ] Schema 노드 필터링
- [ ] SQL 생성 시 힌트 제공

---

## 우선순위

**즉시 구현 필요:**
1. Phase 1 (백엔드 API)
2. Phase 2 (Data Sources 화면)
3. Phase 4 (PromptInput 드롭다운)

**이후 구현:**
4. Phase 3 (다양한 Import Modal)
5. Phase 5 (Agent 최적화)

---

**Status:** Ready for implementation  
**Last Updated:** 2025-10-23

