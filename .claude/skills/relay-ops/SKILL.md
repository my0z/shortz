---
name: relay-ops
description: Fix relay server workflow mistakes for the shortz project. Trigger on terminal output showing errors like "python not found" "No module named src" "externally-managed-environment" "can't find session" "Permission denied (publickey)" "No such file or directory" on scp, a "~/shortz/shortz" prompt, or a broken SSH pipe mid-render. Identifies which environment the user is actually in and gives the exact recovery commands.
---

# relay 작업 환경 점검

사용자가 붙여준 터미널 출력에서 프롬프트와 에러를 보고 상태를 먼저 판정한 뒤 딱 필요한 명령만 줍니다. 설명은 한두 줄로 끝냅니다.

## 1. 지금 어디에 있는지 판정

| 프롬프트 | 위치 | 판단 |
|---|---|---|
| `~ $` 또는 경로에 `com.termux` | 폰 Termux | relay가 아님. 여기서는 ssh와 scp만 함 |
| `ubuntu@relay:~$` | relay 홈 | `cd ~/shortz` 필요 |
| `ubuntu@relay:~/shortz$` | 정상 | venv 표시 확인 |
| `ubuntu@relay:~/shortz/shortz$` | 중첩 폴더 | `cd ~/shortz`로 이동 |
| 앞에 `(.venv)` 없음 | venv 꺼짐 | `source .venv/bin/activate` |
| `PS C:\...>` | Windows | scp 경로를 `$env:USERPROFILE\Downloads\`로 |

## 2. 에러별 즉시 조치

| 에러 | 원인 | 명령 |
|---|---|---|
| `Command 'python' not found` | venv 꺼짐 | `cd ~/shortz && source .venv/bin/activate` |
| `No module named 'src'` | 폴더가 아니거나 Termux | 위와 같음. Termux면 `ssh ubuntu@relay` |
| `No module named 'numpy'` 등 | Termux에서 실행 중 | Termux에는 설치하지 않음. relay로 이동 |
| `externally-managed-environment` | venv 없이 pip | `source .venv/bin/activate` 후 재시도 |
| `can't find session: shortz` | tmux 세션 종료됨 | `tmux new -s shortz` |
| `Permission denied (publickey)` on scp | relay 안에서 scp 실행 | `exit`로 나가서 Termux에서 실행 |
| scp `No such file or directory` (원격) | 파일이 중첩 폴더에 생성됨 | `ssh` 후 `find ~ -name "<이름>.mp4"` |
| scp `No such file or directory` (로컬) | Termux 저장소 폴더 없음 | `termux-setup-storage` 후 `~/storage/downloads/` 사용 |
| `Software caused connection abort` | SSH 끊김 | tmux 안이면 `tmux attach -t shortz`. 아니면 재실행 |
| `moov atom not found` | 렌더링 중 프로세스 사망 | tmux 안에서 재실행 |
| `unrecognized arguments` | 옛 코드 | `git pull origin <브랜치>` 후 `find . -name __pycache__ -exec rm -rf {} +` |
| 이전 값이 안 바뀜 (AttributeError 등) | pyc 캐시 | 위 캐시 삭제 명령 |

## 3. 표준 시작 순서

어떤 상황이든 아래로 돌아오면 정상 상태입니다.

```
ssh ubuntu@relay
tmux new -s shortz      # 이미 있으면 tmux attach -t shortz
cd ~/shortz
source .venv/bin/activate
git pull origin <현재 브랜치>
```

## 4. 다운로드 표준

relay에서 `exit`로 나온 뒤 로컬에서 실행합니다.

```
scp ubuntu@relay:~/shortz/output/<이름>.mp4 ~/storage/downloads/<이름>.mp4
```

## 5. 하지 말 것

- Termux에 `pip install`이나 프로젝트 실행을 시키지 않습니다
- relay 안에서 scp를 시키지 않습니다
- 렌더링 중인 tmux 세션을 kill하지 않습니다
- 렌더링 두 개를 동시에 돌리지 않습니다
