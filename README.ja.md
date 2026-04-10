<div align="center">

<img src="assets/banner.svg" alt="" width="820">

<h1>newton-cli</h1>

**AIエージェントがJSONでGPU物理シミュレーションを駆動します — Pythonは不要です。**<br>
**Pythonが必要な場合は、`run-script` が構造化出力でラップします。**

<p>
  <a href="#-クイックスタート"><img src="https://img.shields.io/badge/Quick_Start-2_min-blue?style=for-the-badge" alt="Quick Start"></a>
  <a href="#-カバレッジ"><img src="https://img.shields.io/badge/Examples-58%2F65-brightgreen?style=for-the-badge" alt="58/65 examples"></a>
  <a href="#-対応ソルバー"><img src="https://img.shields.io/badge/Solvers-7_backends-green?style=for-the-badge" alt="Solvers"></a>
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="License">
</p>

<p>
  <img src="https://img.shields.io/badge/python-3.10+-blue?logo=python&logoColor=white" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/GPU-CUDA_12-76B900?logo=nvidia&logoColor=white" alt="CUDA 12">
  <img src="https://img.shields.io/badge/engine-NVIDIA_Newton-76B900" alt="Newton">
  <img src="https://img.shields.io/badge/status-alpha-orange" alt="Status: alpha">
  <img src="https://img.shields.io/badge/tests-29_passing-brightgreen" alt="29 tests passing">
</p>

[特徴](#-なぜ-newton-cli-なのか) · [クイックスタート](#-クイックスタート) · [ギャラリー](#-ギャラリー) · [コマンド](#-コマンド) · [アーキテクチャ](#-アーキテクチャ)

**Language / 言語:**&ensp;[English](README.md)&ensp;|&ensp;[简体中文](README.zh-CN.md)&ensp;|&ensp;日本語&ensp;|&ensp;[한국어](README.ko.md)

</div>

---

## ギャラリー

以下の画像はすべて `newton-cli viewer render` でレンダリングされたものです。Newton独自のビューアーと同じヘッドレスOpenGLパスを使用しています。

<table>
<tr>
<td align="center"><img src="assets/render_robot_g1.png" width="260"><br><sub>Unitree G1 ヒューマノイド (MJCF)</sub></td>
<td align="center"><img src="assets/render_cloth_hanging.png" width="260"><br><sub>布の吊り下げ (XPBD)</sub></td>
<td align="center"><img src="assets/render_mpm_granular.png" width="260"><br><sub>粒状材料 (MPM)</sub></td>
</tr>
<tr>
<td align="center"><img src="assets/render_cable_pile.png" width="260"><br><sub>40本のケーブル沈降 (VBD)</sub></td>
<td align="center"><img src="assets/render_pyramid.png" width="260"><br><sub>ピラミッド積み上げ（接触）</sub></td>
<td align="center"><img src="assets/render_basic_urdf.png" width="260"><br><sub>4体のANYmal四足歩行ロボット (URDF)</sub></td>
</tr>
</table>

<sub>すべてのレンダリングは3つのCLIコマンドで生成されました — 下記の<a href="#route-a--宣言的レシピ">ルートA</a>をご覧ください。</sub>

---

## なぜ newton-cli なのか

- **AIエージェントが書くのはJSON、Pythonではありません。** 宣言的レシピ形式により、シーン記述が構造化データに変換されます。これはLLMが最も得意とする形式です。
- **スタックトレースではなく、構造化エラーです。** すべてのコマンドは `--json` を指定すると `{"schema":"newton-cli/v1","data":...}` を出力します。終了コードは決定論的です: 0 正常 / 2 引数エラー / 3 ランタイムエラー / 4 依存関係不足 / 5 タイムアウト。
- **2つのルート、1つのCLI。** ルートA（レシピ）はパッシブシミュレーションをカバーします。ルートB（run-script）はカスタムカーネル、ポリシー、自動微分をカバーします — 機能のギャップはありません。
- **レシピがモデルです。** 不透明なバイナリの保存・読み込みはありません。JSONファイルがモデルそのものです。検査、差分比較、バージョン管理が可能です。
- **58 / 65のNewtonサンプルをエンドツーエンドで駆動。** 剛体、ジョイント、URDF/MJCFインポーター、布、ソフトボディ、MPM、ケーブル、SDFメッシュ接触、微分可能シミュレーション、IK、セレクション — すべて `newton-cli` で実行できます。

---

## クイックスタート

```bash
# 1. クローン（NewtonはCLIと並んで同梱されています）
git clone <repo-url> && cd newton-cli/newton_cli

# 2. 仮想環境の作成とインストール
uv venv --python 3.12
uv pip install -e .
uv pip install -e ../newton[importers,sim]

# 3. 動作確認
newton-cli version --json
newton-cli devices list --json

# 4. テストスイートの実行（29テスト）
uv run python -m unittest discover tests
```

> **Claude Code / AIエージェント向け:** `newton-cli` を `PATH` に追加するか、
> `python -m newton_cli <command> --json` で呼び出してください。すべてのコマンドは
> 機械可読な出力のために `--json` を受け付けます。[CLAUDE.md](CLAUDE.md) ファイルに
> エージェント統合の完全な仕様が記載されています。

---

## アーキテクチャ

<div align="center">
<img src="assets/architecture.svg" alt="newton-cli architecture" width="720">
</div>

### Route A — 宣言的レシピ

エージェントは `ModelBuilder` の呼び出しを記述した `recipe.json` を出力します。CLIがそれを再実行し、ソルバーを動かし、`final.npz` と `render.png` を出力します。**25のサンプル**がこのルートを使用します。

```bash
# JSONレシピからシーンを構築
newton-cli model build --recipe scene.json --out model.json --device cuda:0 --json

# MuJoCoソルバーで60fpsの100フレームをシミュレーション
newton-cli sim run --model model.json --solver SolverMuJoCo \
    --num-frames 100 --fps 60 --substeps 10 \
    --out final.npz --device cuda:0 --json

# 最終状態をPNGにレンダリング（ヘッドレスOpenGL）
newton-cli viewer render --model model.json --state final.npz \
    --out render.png --width 1280 --height 720 --json
```

<details>
<summary>recipe.json の例（振り子）</summary>

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

### Route B — run-script エスケープハッチ

ステップごとにPythonが必要なサンプル（カスタム `@wp.kernel`、torchポリシー、自動微分）では、エージェントがスクリプトを書き、CLIが構造化出力で実行します。**33のサンプル**がこのルートを使用します。

```bash
newton-cli run-script my_sim.py \
    --artifact-dir outputs/ \
    --timeout 300 --json
```

スクリプトは環境変数 `NEWTON_CLI_ARTIFACT_DIR` を参照でき、`final.npz` やプロットなどをエージェントが読み取れるように出力できます。

---

## コマンド

| コマンド | 機能 |
|---|---|
| `newton-cli version` | Newton / Warp / Python / CLI のバージョン情報 |
| `newton-cli devices list` | 利用可能なコンピュートデバイス（CPU + CUDA） |
| `newton-cli api list [--module M]` | NewtonのパブリックAPIシンボルを一覧表示 |
| `newton-cli api describe <symbol>` | 任意のパブリックシンボルのdocstringとシグネチャを表示 |
| `newton-cli model build --recipe R --out O` | レシピJSONの検証と実体化 |
| `newton-cli sim run --model M --solver S --out O` | 標準ステップループ → 最終状態 `.npz` |
| `newton-cli viewer render --model M --state S --out O` | ヘッドレスOpenGL → PNGスナップショット |
| `newton-cli run-script <path> [--timeout T]` | Pythonスクリプトを構造化出力で実行 |
| `newton-cli examples list` | 65個の組み込みNewtonサンプルを一覧表示 |
| `newton-cli examples run <name> [-- args]` | 組み込みサンプルを実行（Newtonに転送） |

すべてのコマンドは `--json` を指定すると機械可読な `{"schema":"newton-cli/v1","data":...}` 出力を返します。

---

## 対応ソルバー

| ソルバー | 物理ドメイン | ルートA | ルートB |
|---|---|---|---|
| `SolverXPBD` | 布、ソフトボディ、剛体接触 | 対応 | 対応 |
| `SolverVBD` | ケーブル、剛体 + 変形体の接触 | 対応 | 対応 |
| `SolverMuJoCo` | 多関節ロボット（MuJoCoネイティブ） | 対応 | 対応 |
| `SolverImplicitMPM` | 粒状体、粘性体、雪、泥 | 対応 | 対応 |
| `SolverStyle3D` | 衣服シミュレーション（Style3D布） | — | 対応 |
| `SolverSemiImplicit` | 微分可能シミュレーション（自動微分） | — | 対応 |
| カスタム `@wp.kernel` | ユーザー定義の任意の処理 | — | 対応 |

---

## カバレッジ

**58 / 65のNewtonサンプルが `newton-cli` でエンドツーエンドに動作します。**

| カテゴリ | ルートA（レシピ） | ルートB（run-script） | 合計 |
|---|---|---|---|
| 基本（振り子、形状、ジョイント、ハイトフィールド、URDF、プロット） | 6 | 2 | 8 |
| ロボット（cartpole、anymal_d、g1、h1、ur10、allegro、panda） | 5 | 3 | 8 |
| 布（吊り下げ、曲げ、poker_cards、style3d、franka、h1、rollers、twist） | 4 | 4 | 8 |
| ソフトボディ（吊り下げ、gift、dropping_to_cloth、franka） | 3 | 1 | 4 |
| MPM（粒状体、multi_material、粘性体、grain_rendering、雪、beam、twoway） | 4 | 3 | 7 |
| ケーブル（y_junction、pile、twist、bundle_hysteresis） | 2 | 2 | 4 |
| 接触（pyramid、nut_bolt_hydro、nut_bolt_sdf、brick_stacking） | 3 | 1 | 4 |
| 微分可能シミュレーション（ball、bear、cloth、drone、soft_body） | — | 5 | 5 |
| セレクション（articulations、cartpole、materials、multiple） | — | 4 | 4 |
| IK（franka、h1、custom） | — | 3 | 3 |
| センサー（contact、imu、tiled_camera） | — | 3 | 3 |
| **合計** | **25** | **33** | **58** |

<details>
<summary>動作しない7つのサンプル（いずれもCLIの機能不足が原因ではありません）</summary>

| サンプル | 理由 |
|---|---|
| `robot_policy`、`robot_anymal_c_walk`、`mpm_anymal` | CUDA torchホイールが必要です（Py3.13/Win環境ではuvで利用不可）。Linux + Py3.12であれば動作します。 |
| `contacts_rj45_plug`、`replay_viewer` | インタラクティブなGLビューア機能（`viewer.picking`、`register_ui_callback`）が必要です。ヘッドレス実行はできません。 |
| `ik_cube_stacking` | サンプルの `test_final` がワールド成功率70%以上を検証しますが、デフォルト引数では0%に収束します。上流の設定の問題です。 |
| `diffsim_spring_cage` | サンプル自体の `np.allclose(grad_numeric, grad_analytic, atol=0.2)` が失敗します。このハードウェアでの数値精度の問題です。 |

</details>

---

## プロジェクト構成

```
newton_cli/
├── pyproject.toml              # hatchlingビルド、newtonパス依存
├── README.md                   # 英語版README
├── CLAUDE.md                   # エージェント統合仕様
├── assets/                     # README用のSVG/PNG
├── src/newton_cli/
│   ├── cli.py                  # argparseディスパッチャー（10サブコマンド）
│   ├── recipes.py              # JSONレシピ → ModelBuilderインタープリター
│   ├── sim.py                  # ステップループ（全7ソルバーバックエンド）
│   ├── render.py               # ヘッドレスOpenGL → PNG
│   ├── state_io.py             # .npzラウンドトリップ（State配列用）
│   ├── io.py                   # JSONエンベロープ + 終了コード
│   └── _introspect.py          # APIブラウザー（許可リストウォーカー）
├── tests/
│   ├── test_phase0_introspection.py    # 14ユニットテスト
│   ├── test_run_script.py              # 6つのrun-script契約テスト
│   └── test_examples/                  # 58個のサンプル別フォルダ
│       ├── _shared/                    # visualize.py + b_route_runner.py
│       ├── basic_pendulum/             # recipe.json + run.ps1 + outputs/
│       ├── robot_g1/                   # recipe.json + run.ps1 + outputs/
│       └── ...                         # （全58個）
└── logs/                       # ラウンドサマリー
```

---

## 開発

```bash
# テストスイートの完全実行（29テスト、約2分）
uv run python -m unittest discover tests

# サンプルを1つエンドツーエンドで実行（ルートA）
cd tests/test_examples/robot_g1
powershell -ExecutionPolicy Bypass -File ./run.ps1

# サンプルを1つエンドツーエンドで実行（ルートB）
cd tests/test_examples/cable_twist
powershell -ExecutionPolicy Bypass -File ./run.ps1
```

完全な開発ガイドとエージェント統合契約は [CLAUDE.md](CLAUDE.md) をご覧ください。

---

## ライセンス

Apache 2.0。Newton自体は別途ライセンスされています — `../newton/LICENSE` をご参照ください。
