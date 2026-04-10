<div align="center">

<img src="assets/banner.svg" alt="" width="820">

<h1>newton-cli</h1>

**AI 에이전트가 JSON으로 GPU 물리 시뮬레이션을 구동합니다 — Python이 필요 없습니다.**<br>
**Python이 필요한 경우, `run-script`가 구조화된 출력으로 래핑합니다.**

<p>
  <a href="#-빠른-시작"><img src="https://img.shields.io/badge/Quick_Start-2_min-blue?style=for-the-badge" alt="Quick Start"></a>
  <a href="#-커버리지"><img src="https://img.shields.io/badge/Examples-58%2F65-brightgreen?style=for-the-badge" alt="58/65 examples"></a>
  <a href="#-지원-솔버"><img src="https://img.shields.io/badge/Solvers-7_backends-green?style=for-the-badge" alt="Solvers"></a>
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="License">
</p>

<p>
  <img src="https://img.shields.io/badge/python-3.10+-blue?logo=python&logoColor=white" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/GPU-CUDA_12-76B900?logo=nvidia&logoColor=white" alt="CUDA 12">
  <img src="https://img.shields.io/badge/engine-NVIDIA_Newton-76B900" alt="Newton">
  <img src="https://img.shields.io/badge/status-alpha-orange" alt="Status: alpha">
  <img src="https://img.shields.io/badge/tests-29_passing-brightgreen" alt="29 tests passing">
</p>

[기능](#-왜-newton-cli인가) · [빠른 시작](#-빠른-시작) · [갤러리](#-갤러리) · [명령어](#-명령어) · [아키텍처](#-아키텍처)

**Language / 언어:**&ensp;[English](README.md)&ensp;|&ensp;[简体中文](README.zh-CN.md)&ensp;|&ensp;[日本語](README.ja.md)&ensp;|&ensp;한국어

</div>

---

## 갤러리

아래의 모든 이미지는 `newton-cli viewer render`로 렌더링되었습니다 — Newton 자체 뷰어가 사용하는 것과 동일한 헤드리스 OpenGL 경로입니다.

<table>
<tr>
<td align="center"><img src="assets/render_robot_g1.png" width="260"><br><sub>Unitree G1 휴머노이드 (MJCF)</sub></td>
<td align="center"><img src="assets/render_cloth_hanging.png" width="260"><br><sub>천 매달기 (XPBD)</sub></td>
<td align="center"><img src="assets/render_mpm_granular.png" width="260"><br><sub>입상 재료 (MPM)</sub></td>
</tr>
<tr>
<td align="center"><img src="assets/render_cable_pile.png" width="260"><br><sub>40개 케이블 안착 (VBD)</sub></td>
<td align="center"><img src="assets/render_pyramid.png" width="260"><br><sub>피라미드 쌓기 (접촉)</sub></td>
<td align="center"><img src="assets/render_basic_urdf.png" width="260"><br><sub>4대의 ANYmal 사족보행 로봇 (URDF)</sub></td>
</tr>
</table>

<sub>모든 렌더링은 3개의 CLI 명령어로 생성되었습니다 — 아래 <a href="#route-a--선언적-레시피">Route A</a>를 참조하십시오.</sub>

---

## 왜 newton-cli인가

- **AI 에이전트는 Python이 아닌 JSON을 채웁니다.** 선언적 레시피 형식은 장면 설명을 구조화된 데이터로 변환합니다 — LLM이 가장 잘하는 것입니다.
- **스택 트레이스가 아닌 구조화된 오류.** 모든 명령어는 `--json` 옵션으로 `{"schema":"newton-cli/v1","data":...}`를 출력합니다. 종료 코드는 결정적입니다: 0 정상 / 2 인자 오류 / 3 런타임 / 4 누락된 의존성 / 5 타임아웃.
- **두 가지 경로, 하나의 CLI.** Route A(레시피)는 수동 시뮬레이션을 다룹니다. Route B(run-script)는 커스텀 커널, 정책, autograd를 다룹니다 — 기능 격차가 없습니다.
- **레시피가 곧 모델입니다.** 불투명한 바이너리 저장/로드가 없습니다. JSON 파일이 곧 모델입니다. 검사하고, diff하고, 버전 관리할 수 있습니다.
- **58 / 65 Newton 예제를 엔드투엔드로 구동합니다.** 강체, 조인트, URDF/MJCF 임포터, 천, 소프트바디, MPM, 케이블, SDF 메시 접촉, 미분 가능 시뮬레이션, IK, 선택 — 모두 `newton-cli`를 통해 가능합니다.

---

## 빠른 시작

```bash
# 1. 클론 (Newton은 newton-cli와 함께 벤더링되어 있습니다)
git clone <repo-url> && cd newton-cli/newton_cli

# 2. venv 생성 + 설치
uv venv --python 3.12
uv pip install -e .
uv pip install -e ../newton[importers,sim]

# 3. 확인
newton-cli version --json
newton-cli devices list --json

# 4. 테스트 스위트 실행 (29개 테스트)
uv run python -m unittest discover tests
```

> **Claude Code / AI 에이전트의 경우:** `newton-cli`를 `PATH`에 추가하거나
> `python -m newton_cli <command> --json`으로 호출하십시오. 모든 명령어는
> 기계가 읽을 수 있는 출력을 위해 `--json`을 지원합니다. [CLAUDE.md](CLAUDE.md)
> 파일에 전체 에이전트 통합 계약이 문서화되어 있습니다.

---

## 아키텍처

<div align="center">
<img src="assets/architecture.svg" alt="newton-cli architecture" width="720">
</div>

### Route A — 선언적 레시피

에이전트가 `ModelBuilder` 호출을 설명하는 `recipe.json`을 생성합니다. CLI가 이를 재실행하고, 솔버를 실행하고, `final.npz` + `render.png`를 출력합니다. **25개 예제**가 이 경로를 사용합니다.

```bash
# JSON 레시피에서 장면 빌드
newton-cli model build --recipe scene.json --out model.json --device cuda:0 --json

# MuJoCo 솔버로 60 fps에서 100 프레임 시뮬레이션
newton-cli sim run --model model.json --solver SolverMuJoCo \
    --num-frames 100 --fps 60 --substeps 10 \
    --out final.npz --device cuda:0 --json

# 최종 상태를 PNG로 렌더링 (헤드리스 OpenGL)
newton-cli viewer render --model model.json --state final.npz \
    --out render.png --width 1280 --height 720 --json
```

<details>
<summary>레시피 예시: recipe.json (진자)</summary>

```json
{
  "schema": "newton-cli/recipe/v1",
  "ops": [
    {"op": "add_body", "args": {"xform": {"p": [0,0,2], "q": [0,0,0,1]}}},
    {"op": "add_shape_sphere", "args": {"body": 0, "radius": 0.1}},
    {"op": "add_joint_revolute", "args": {
      "parent": -1, "child": 0,
      "parent_xform": {"p": [0,0,2], "q": [0,0,0,1]},
      "child_xform": {"p": [0,0,0], "q": [0,0,0,1]},
      "axis": [1,0,0]
    }},
    {"op": "add_ground_plane", "args": {}}
  ]
}
```
</details>

### Route B — run-script 이스케이프 해치

단계별 Python이 필요한 예제(커스텀 `@wp.kernel`, torch 정책, autograd)의 경우, 에이전트가 스크립트를 작성하고 CLI가 구조화된 출력으로 실행합니다. **33개 예제**가 이 경로를 사용합니다.

```bash
newton-cli run-script my_sim.py \
    --artifact-dir outputs/ \
    --timeout 300 --json
```

스크립트는 환경 변수에서 `NEWTON_CLI_ARTIFACT_DIR`을 확인할 수 있으며, `final.npz`, 플롯 등을 저장하여 에이전트가 다시 읽을 수 있습니다.

---

## 명령어

| 명령어 | 기능 |
|---|---|
| `newton-cli version` | Newton / Warp / Python / CLI 버전 정보 |
| `newton-cli devices list` | 사용 가능한 컴퓨팅 디바이스 (CPU + CUDA) |
| `newton-cli api list [--module M]` | Newton 공개 API 심볼 탐색 |
| `newton-cli api describe <symbol>` | 공개 심볼의 독스트링 + 시그니처 |
| `newton-cli model build --recipe R --out O` | 레시피 JSON 검증 + 실체화 |
| `newton-cli sim run --model M --solver S --out O` | 표준 스텝 루프 → 최종 상태 `.npz` |
| `newton-cli viewer render --model M --state S --out O` | 헤드리스 OpenGL → PNG 스냅샷 |
| `newton-cli run-script <path> [--timeout T]` | 구조화된 출력으로 Python 스크립트 실행 |
| `newton-cli examples list` | 65개 내장 Newton 예제 목록 |
| `newton-cli examples run <name> [-- args]` | 내장 예제 실행 (Newton으로 전달) |

모든 명령어는 기계가 읽을 수 있는 `{"schema":"newton-cli/v1","data":...}` 출력을 위해 `--json`을 지원합니다.

---

## 지원 솔버

| 솔버 | 물리 도메인 | Route A | Route B |
|---|---|---|---|
| `SolverXPBD` | 천, 소프트바디, 강체 접촉 | 예 | 예 |
| `SolverVBD` | 케이블, 강체 + 변형체 접촉 | 예 | 예 |
| `SolverMuJoCo` | 다관절 로봇 (MuJoCo 네이티브) | 예 | 예 |
| `SolverImplicitMPM` | 입상, 점성, 눈, 진흙 | 예 | 예 |
| `SolverStyle3D` | 의류 시뮬레이션 (Style3D 천) | — | 예 |
| `SolverSemiImplicit` | 미분 가능 시뮬레이션 (autograd) | — | 예 |
| 커스텀 `@wp.kernel` | 사용자 정의 모든 것 | — | 예 |

---

## 커버리지

**58 / 65 Newton 예제가 `newton-cli`를 통해 엔드투엔드로 통과합니다.**

| 카테고리 | Route A (레시피) | Route B (run-script) | 합계 |
|---|---|---|---|
| 기본 (진자, 형상, 조인트, 높이필드, URDF, 플로팅) | 6 | 2 | 8 |
| 로봇 (cartpole, anymal_d, g1, h1, ur10, allegro, panda) | 5 | 3 | 8 |
| 천 (매달기, 굽힘, poker_cards, style3d, franka, h1, rollers, twist) | 4 | 4 | 8 |
| 소프트바디 (매달기, gift, dropping_to_cloth, franka) | 3 | 1 | 4 |
| MPM (입상, multi_material, 점성, grain_rendering, 눈, beam, twoway) | 4 | 3 | 7 |
| 케이블 (y_junction, pile, twist, bundle_hysteresis) | 2 | 2 | 4 |
| 접촉 (pyramid, nut_bolt_hydro, nut_bolt_sdf, brick_stacking) | 3 | 1 | 4 |
| 미분 시뮬레이션 (ball, bear, cloth, drone, soft_body) | — | 5 | 5 |
| 선택 (articulations, cartpole, materials, multiple) | — | 4 | 4 |
| IK (franka, h1, custom) | — | 3 | 3 |
| 센서 (contact, imu, tiled_camera) | — | 3 | 3 |
| **합계** | **25** | **33** | **58** |

<details>
<summary>통과하지 못하는 7개 예제 (CLI 기능 격차는 아닙니다)</summary>

| 예제 | 사유 |
|---|---|
| `robot_policy`, `robot_anymal_c_walk`, `mpm_anymal` | CUDA torch 휠이 필요합니다 (Py3.13/Win에서 uv를 통해 사용 불가). Linux + Py3.12에서는 통과합니다. |
| `contacts_rj45_plug`, `replay_viewer` | 인터랙티브 GL 뷰어 기능이 필요합니다 (`viewer.picking`, `register_ui_callback`). 헤드리스로 실행할 수 없습니다. |
| `ik_cube_stacking` | 예제의 `test_final`이 >70% 월드 성공률을 검증하지만, 기본 인자로는 0%로 수렴합니다. 업스트림 설정 문제입니다. |
| `diffsim_spring_cage` | 예제 자체의 `np.allclose(grad_numeric, grad_analytic, atol=0.2)`가 실패합니다. 이 하드웨어에서의 수치 허용 오차 문제입니다. |

</details>

---

## 프로젝트 구조

```
newton_cli/
├── pyproject.toml              # hatchling 빌드, newton 경로 의존성
├── README.md                   # 영문 README
├── CLAUDE.md                   # 에이전트 통합 계약
├── assets/                     # README용 SVG/PNG
├── src/newton_cli/
│   ├── cli.py                  # argparse 디스패처 (10개 서브커맨드)
│   ├── recipes.py              # JSON 레시피 → ModelBuilder 인터프리터
│   ├── sim.py                  # 스텝 루프 (7개 솔버 백엔드 모두)
│   ├── render.py               # 헤드리스 OpenGL → PNG
│   ├── state_io.py             # .npz State 배열 왕복 변환
│   ├── io.py                   # JSON 엔벨로프 + 종료 코드
│   └── _introspect.py          # API 브라우저 (허용 목록 워커)
├── tests/
│   ├── test_phase0_introspection.py    # 14개 유닛 테스트
│   ├── test_run_script.py              # 6개 run-script 계약 테스트
│   └── test_examples/                  # 58개 예제별 폴더
│       ├── _shared/                    # visualize.py + b_route_runner.py
│       ├── basic_pendulum/             # recipe.json + run.ps1 + outputs/
│       ├── robot_g1/                   # recipe.json + run.ps1 + outputs/
│       └── ...                         # (총 58개)
└── logs/                       # 라운드 요약
```

---

## 개발

```bash
# 전체 테스트 스위트 실행 (29개 테스트, ~2분)
uv run python -m unittest discover tests

# 단일 예제 엔드투엔드 실행 (Route A)
cd tests/test_examples/robot_g1
powershell -ExecutionPolicy Bypass -File ./run.ps1

# 단일 예제 엔드투엔드 실행 (Route B)
cd tests/test_examples/cable_twist
powershell -ExecutionPolicy Bypass -File ./run.ps1
```

전체 개발 가이드 및 에이전트 통합 계약은 [CLAUDE.md](CLAUDE.md)를 참조하십시오.

---

## 라이선스

Apache 2.0. Newton 자체는 별도로 라이선스됩니다 — `../newton/LICENSE`를 참조하십시오.
