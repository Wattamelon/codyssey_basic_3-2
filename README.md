# Mini Git

메모리에서 동작하는 CLI 기반 Mini Git입니다. 실제 Git 전체가 아니라 커밋·브랜치·그래프 탐색·검색·정렬의 핵심 구조를 학습하기 위한 프로그램입니다.

## 실행 방법

Python 3.10 이상이 필요합니다.

```bash
python main.py
```

종료하려면 `exit` 또는 `quit`을 입력합니다. 명령어는 대소문자를 구분하지 않습니다.

```text
mini-git> INIT "Alice"
mini-git> commit "Initial commit"
mini-git> quit
```

공백을 포함하는 사용자명·커밋 메시지·검색어는 따옴표로 감쌉니다.

## 지원 명령어

| 명령어 | 설명 |
|---|---|
| `INIT <user_name>` | 저장소를 초기화하고 `main` 브랜치와 현재 사용자를 설정합니다. |
| `COMMIT <message>` | 현재 브랜치 HEAD를 부모로 하는 새 커밋을 만듭니다. |
| `BRANCH <branch_name>` | 현재 HEAD를 가리키는 새 브랜치를 만듭니다. |
| `SWITCH <branch_name>` | 현재 작업 브랜치를 바꿉니다. |
| `LOG` | 저장소 전체 커밋을 부모가 자식보다 먼저 나오게 출력합니다. |
| `LOG --sort-by=date` | 전체 커밋을 timestamp 오름차순으로 출력합니다. |
| `LOG --sort-by=author` | 전체 커밋을 author 오름차순으로 출력합니다. |
| `ANCESTORS <commit_hash>` | 지정 커밋을 제외한 모든 조상을 출력합니다. |
| `PATH <commit1> <commit2>` | 부모-자식 연결을 양방향으로 보고 최단 경로를 출력합니다. |
| `SEARCH <keyword>` | 메시지 토큰 역색인으로 커밋을 검색합니다. |
| `SEARCH --author=<name>` | 작성자 역색인으로 커밋을 검색합니다. |
| `exit`, `quit` | 프로그램을 종료합니다. |

### 실행 예시

```text
mini-git> init "Alice"
Initialized repository.
Current branch: main
Current user: Alice

mini-git> commit "Initial commit"
[main c000001] Initial commit

mini-git> branch feature
Created branch: feature

mini-git> switch feature
Switched to branch: feature

mini-git> commit "Add login feature"
[feature c000002] Add login feature

mini-git> switch main
Switched to branch: main

mini-git> commit "Add payment feature"
[main c000003] Add payment feature

mini-git> path c000002 c000003
Path: c000002 -> c000001 -> c000003

mini-git> search login
Found 1 commit:
- c000002: Add login feature
```

## 자료구조 설계

### Commit

커밋 하나는 아래 필드를 가집니다.

```text
hash       고유 커밋 ID
message    커밋 메시지
author     작성자
timestamp  생성 시각
parents    부모 커밋 해시 목록
```

커밋은 부모를 가리키므로 그래프를 이룹니다. 새 커밋은 기존 커밋만 부모로 가리키므로 순환이 없는 DAG로 유지됩니다.

### Repository

| 상태 | 구조 | 역할 |
|---|---|---|
| 커밋 저장소 | `hash -> Commit` 딕셔너리 | 해시로 원본 커밋을 빠르게 찾습니다. |
| 브랜치 표 | `branch_name -> head_hash` 딕셔너리 | 브랜치가 가리키는 HEAD를 기억합니다. |
| 현재 브랜치 | 문자열 | 지금 작업 중인 브랜치 이름입니다. |
| 키워드 역색인 | `keyword -> [hash]` | 키워드 검색 후보를 바로 찾습니다. |
| 작성자 역색인 | `author -> [hash]` | 작성자 검색 후보를 바로 찾습니다. |

브랜치는 커밋을 복사하지 않고 커밋 해시만 가리키는 포인터입니다.

## 핵심 알고리즘

| 기능 | 알고리즘 | 시간복잡도 |
|---|---|---|
| 해시로 커밋 조회 | `dict` 조회 | 평균 O(1) |
| 기본 LOG | 부모 우선 DFS | O(V + E) |
| ANCESTORS | 부모 방향 DFS + `visited` | O(V + E) |
| PATH | 무방향 BFS | 현재 구현은 자식 검색을 위해 커밋을 확인하므로 대략 O(V²) |
| SEARCH | 역색인 조회 후 해시로 원본 조회 | 평균 O(1) + O(K) |
| LOG 정렬 | 삽입 정렬 | 평균·최악 O(n²) |

`PATH`는 원래 저장된 `자식 -> 부모` 관계를 탐색할 때만 `부모 <-> 자식` 관계로 해석합니다. 여러 최단 경로가 있으면 해시 경로 문자열 기준 사전순으로 가장 작은 경로를 선택합니다.

정렬은 `sorted()`와 `list.sort()` 없이 직접 구현한 삽입 정렬을 사용합니다. 같은 정렬 키에서는 기본 로그 순서를 유지하는 안정 정렬입니다.

## 제약사항 준수

- Python 3.10 이상에서 실행합니다.
- 그래프 전용 라이브러리를 사용하지 않습니다.
- `sorted()`와 `list.sort()`를 사용하지 않습니다.
- 탐색·정렬·인덱싱은 `Repository`의 독립 메서드로 분리했습니다.
- 주요 클래스와 메서드에 docstring을 작성했습니다.
- 데이터는 메모리에만 보관합니다.

## 오류 처리

| 상황 | 예시 결과 |
|---|---|
| 인자가 부족하거나 많음 | `Invalid args` |
| 없는 브랜치 전환 | `Unknown branch: <name>` |
| 없는 커밋 조회 | `Unknown commit: <hash>` |
| 초기화 전 저장소 기능 사용 | `Repository not initialized` |

## 알려진 제한과 보너스 과제

다음은 이번 필수 구현 범위에서 제외했습니다.

- 파일 내용 추적과 파일 저장
- 네트워크 통신과 원격 저장소
- `diff <file1> <file2>`
- `merge <branch_name>`와 부모가 2개인 merge commit 생성
- 정렬 알고리즘 두 가지 이상의 성능 비교
