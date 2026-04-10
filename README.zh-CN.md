<div align="center">

<img src="assets/banner.svg" alt="" width="820">

<h1>newton-cli</h1>

**让 AI agent 用 JSON 驱动 GPU 物理仿真 —— 无需编写 Python。**<br>
**需要 Python 时，`run-script` 以结构化输出包装执行。**

<p>
  <a href="#-快速开始"><img src="https://img.shields.io/badge/快速开始-2_分钟-blue?style=for-the-badge" alt="Quick Start"></a>
  <a href="#-覆盖率"><img src="https://img.shields.io/badge/示例覆盖-58%2F65-brightgreen?style=for-the-badge" alt="58/65 examples"></a>
  <a href="#-支持的求解器"><img src="https://img.shields.io/badge/求解器-7_个后端-green?style=for-the-badge" alt="Solvers"></a>
  <img src="https://img.shields.io/badge/许可证-MIT-yellow?style=for-the-badge" alt="License">
</p>

<p>
  <img src="https://img.shields.io/badge/python-3.10+-blue?logo=python&logoColor=white" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/GPU-CUDA_12-76B900?logo=nvidia&logoColor=white" alt="CUDA 12">
  <img src="https://img.shields.io/badge/引擎-NVIDIA_Newton-76B900" alt="Newton">
  <img src="https://img.shields.io/badge/状态-alpha-orange" alt="Status: alpha">
  <img src="https://img.shields.io/badge/测试-29_通过-brightgreen" alt="29 tests passing">
</p>

[特性](#-为什么选择-newton-cli) · [快速开始](#-快速开始) · [渲染展示](#-渲染展示) · [命令列表](#-命令列表) · [架构设计](#-架构设计)

**Language / 语言:**&ensp;[English](README.md)&ensp;|&ensp;简体中文&ensp;|&ensp;[日本語](README.ja.md)&ensp;|&ensp;[한국어](README.ko.md)

</div>

---

## 渲染展示

以下每张图都由 `newton-cli viewer render` 渲染生成 —— 和 Newton 自带 OpenGL 查看器使用的是同一套 headless 渲染管线。

<table>
<tr>
<td align="center"><img src="assets/render_robot_g1.png" width="260"><br><sub>Unitree G1 人形机器人 (MJCF)</sub></td>
<td align="center"><img src="assets/render_cloth_hanging.png" width="260"><br><sub>布料悬挂 (XPBD)</sub></td>
<td align="center"><img src="assets/render_mpm_granular.png" width="260"><br><sub>颗粒材料 (MPM)</sub></td>
</tr>
<tr>
<td align="center"><img src="assets/render_cable_pile.png" width="260"><br><sub>40 根缆绳堆叠 (VBD)</sub></td>
<td align="center"><img src="assets/render_pyramid.png" width="260"><br><sub>方块金字塔堆叠（接触）</sub></td>
<td align="center"><img src="assets/render_basic_urdf.png" width="260"><br><sub>4 台 ANYmal 四足机器人 (URDF)</sub></td>
</tr>
</table>

<sub>以上渲染仅需 3 条 CLI 命令 —— 见下方 <a href="#路线-a--声明式-recipe">路线 A</a>。</sub>

---

## 为什么选择 newton-cli

- **AI agent 填 JSON，不写 Python。** 声明式 recipe 格式将场景描述转化为结构化数据 —— 这恰好是 LLM 最擅长的事。
- **结构化错误，而不是堆栈追踪。** 每条命令加 `--json` 输出 `{"schema":"newton-cli/v1","data":...}`。退出码确定性：0 成功 / 2 参数错误 / 3 运行时错误 / 4 依赖缺失 / 5 超时。
- **两条路线，一个 CLI。** 路线 A（recipe）覆盖被动仿真；路线 B（run-script）覆盖自定义 kernel、策略、自动微分 —— 零能力盲区。
- **Recipe 就是模型。** 不需要不透明的二进制存档。JSON 文件本身就是模型，可检查、可 diff、可版本控制。
- **58 / 65 个 Newton 示例端到端驱动。** 刚体、关节、URDF/MJCF 导入器、布料、软体、MPM、缆绳、SDF 网格接触、可微分仿真、IK、selection —— 全部通过 `newton-cli`。

---

## 快速开始

```bash
# 1. 克隆（Newton 作为同级目录一起分发）
git clone https://github.com/Terry-cyx/newton-cli.git && cd newton-cli/newton_cli

# 2. 创建虚拟环境并安装
uv venv --python 3.12
uv pip install -e .
uv pip install -e ../newton[importers,sim]

# 3. 验证安装
newton-cli version --json
newton-cli devices list --json

# 4. 运行测试套件（29 个测试）
uv run python -m unittest discover tests
```

> **Claude Code / AI agent 用户：** 将 `newton-cli` 加入 `PATH`，或通过
> `python -m newton_cli <命令> --json` 调用。每条命令都支持 `--json`
> 输出机器可读的 JSON。完整的 agent 集成契约见 [CLAUDE.md](CLAUDE.md)。

---

## 架构设计

<div align="center">
<img src="assets/architecture.svg" alt="newton-cli 架构" width="720">
</div>

### 路线 A — 声明式 recipe

Agent 输出一个描述 `ModelBuilder` 调用序列的 `recipe.json`。CLI 重新执行该文件，运行求解器，输出 `final.npz` + `render.png`。**25 个示例**使用此路线。

```bash
# 从 JSON recipe 构建场景
newton-cli model build --recipe scene.json --out model.json --device cuda:0 --json

# 用 MuJoCo 求解器模拟 100 帧 @ 60 fps
newton-cli sim run --model model.json --solver SolverMuJoCo \
    --num-frames 100 --fps 60 --substeps 10 \
    --out final.npz --device cuda:0 --json

# 将最终状态渲染为 PNG（headless OpenGL）
newton-cli viewer render --model model.json --state final.npz \
    --out render.png --width 1280 --height 720 --json
```

<details>
<summary>示例 recipe.json（单摆）</summary>

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

### 路线 B — run-script 逃生舱

当示例需要逐步执行 Python（自定义 `@wp.kernel`、torch 策略、自动微分），agent 编写脚本，CLI 在子进程中以结构化输出运行。**33 个示例**使用此路线。

```bash
newton-cli run-script my_sim.py \
    --artifact-dir outputs/ \
    --timeout 300 --json
```

脚本可通过环境变量 `NEWTON_CLI_ARTIFACT_DIR` 将 `final.npz`、图表等产物写入指定目录，供 agent 后续读取。

---

## 命令列表

| 命令 | 功能 |
|---|---|
| `newton-cli version` | 输出 Newton / Warp / Python / CLI 版本 |
| `newton-cli devices list` | 列出可用计算设备（CPU + CUDA） |
| `newton-cli api list [--module M]` | 浏览 Newton 公开 API 符号 |
| `newton-cli api describe <符号>` | 查看任意公开符号的文档和签名 |
| `newton-cli model build --recipe R --out O` | 验证并实例化 recipe JSON |
| `newton-cli sim run --model M --solver S --out O` | 标准步进循环 → 最终状态 `.npz` |
| `newton-cli viewer render --model M --state S --out O` | Headless OpenGL → PNG 快照 |
| `newton-cli run-script <路径> [--timeout T]` | 在子进程中执行 Python 脚本并结构化输出 |
| `newton-cli examples list` | 列出全部 65 个内置 Newton 示例 |
| `newton-cli examples run <名称> [-- 参数]` | 运行内置示例（转发至 Newton） |

所有命令均支持 `--json` 标志，输出机器可读的 `{"schema":"newton-cli/v1","data":...}` 格式。

---

## 支持的求解器

| 求解器 | 物理领域 | 路线 A | 路线 B |
|---|---|---|---|
| `SolverXPBD` | 布料、软体、刚体接触 | 支持 | 支持 |
| `SolverVBD` | 缆绳、刚体 + 可变形接触 | 支持 | 支持 |
| `SolverMuJoCo` | 关节机器人（MuJoCo 原生） | 支持 | 支持 |
| `SolverImplicitMPM` | 颗粒、粘性流体、雪、泥 | 支持 | 支持 |
| `SolverStyle3D` | 服装仿真（Style3D 布料） | — | 支持 |
| `SolverSemiImplicit` | 可微分仿真（autograd） | — | 支持 |
| 自定义 `@wp.kernel` | 任意用户自定义物理 | — | 支持 |

---

## 覆盖率

**58 / 65 个 Newton 示例通过 `newton-cli` 端到端驱动。**

| 类别 | 路线 A (recipe) | 路线 B (run-script) | 合计 |
|---|---|---|---|
| 基础（pendulum, shapes, joints, heightfield, URDF, plotting） | 6 | 2 | 8 |
| 机器人（cartpole, anymal_d, g1, h1, ur10, allegro, panda） | 5 | 3 | 8 |
| 布料（hanging, bending, poker_cards, style3d, franka, h1, rollers, twist） | 4 | 4 | 8 |
| 软体（hanging, gift, dropping_to_cloth, franka） | 3 | 1 | 4 |
| MPM（granular, multi_material, viscous, grain_rendering, snow, beam, twoway） | 4 | 3 | 7 |
| 缆绳（y_junction, pile, twist, bundle_hysteresis） | 2 | 2 | 4 |
| 接触（pyramid, nut_bolt_hydro, nut_bolt_sdf, brick_stacking） | 3 | 1 | 4 |
| 可微分仿真（ball, bear, cloth, drone, soft_body） | — | 5 | 5 |
| Selection（articulations, cartpole, materials, multiple） | — | 4 | 4 |
| IK（franka, h1, custom） | — | 3 | 3 |
| 传感器（contact, imu, tiled_camera） | — | 3 | 3 |
| **合计** | **25** | **33** | **58** |

<details>
<summary>7 个未通过的示例（均非 CLI 能力缺陷）</summary>

| 示例 | 原因 |
|---|---|
| `robot_policy`、`robot_anymal_c_walk`、`mpm_anymal` | 需要 CUDA 版 torch（uv 在 Py3.13/Win 上无法安装）。在 Linux + Py3.12 环境下即可通过。 |
| `contacts_rj45_plug`、`replay_viewer` | 需要交互式 GL 查看器功能（`viewer.picking`、`register_ui_callback`）。无法 headless 运行。 |
| `ik_cube_stacking` | 示例的 `test_final` 断言成功率 >70%，默认参数下收敛至 0%。上游配置问题。 |
| `diffsim_spring_cage` | 示例自身的 `np.allclose(grad_numeric, grad_analytic, atol=0.2)` 断言失败。数值精度问题。 |

</details>

---

## 项目结构

```
newton_cli/
├── pyproject.toml              # hatchling 构建，newton 路径依赖
├── README.md                   # 英文 README
├── README.zh-CN.md             # 本文件
├── CLAUDE.md                   # agent 集成契约
├── assets/                     # SVG/PNG 资源
├── src/newton_cli/
│   ├── cli.py                  # argparse 分发器（10 个子命令）
│   ├── recipes.py              # JSON recipe → ModelBuilder 解释器
│   ├── sim.py                  # 步进循环（7 种求解器后端）
│   ├── render.py               # headless OpenGL → PNG
│   ├── state_io.py             # State 数组 .npz 读写
│   ├── io.py                   # JSON 信封 + 退出码
│   └── _introspect.py          # API 浏览器（白名单遍历）
├── tests/
│   ├── test_phase0_introspection.py    # 14 个单元测试
│   ├── test_run_script.py              # 6 个 run-script 契约测试
│   └── test_examples/                  # 58 个示例文件夹
│       ├── _shared/                    # visualize.py + b_route_runner.py
│       ├── basic_pendulum/             # recipe.json + run.ps1 + outputs/
│       ├── robot_g1/                   # recipe.json + run.ps1 + outputs/
│       └── ...                         # （共 58 个）
└── logs/                       # 各轮总结
```

---

## 开发指南

```bash
# 运行完整测试套件（29 个测试，约 2 分钟）
uv run python -m unittest discover tests

# 端到端运行单个示例（路线 A）
cd tests/test_examples/robot_g1
powershell -ExecutionPolicy Bypass -File ./run.ps1

# 端到端运行单个示例（路线 B）
cd tests/test_examples/cable_twist
powershell -ExecutionPolicy Bypass -File ./run.ps1
```

完整开发指南和 agent 集成契约见 [CLAUDE.md](CLAUDE.md)。

---

## 许可证

MIT。Newton 本身单独授权 —— 见 `../newton/LICENSE`。
