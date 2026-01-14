
# TaskMaster 仕様書（Ebbinghaus Forgetting Curve Based Task Manager）

作成日: 2026-01-08

## 1. 概要

本アプリは、エビングハウスの忘却曲線（想起確率の低下）を前提に、タスクを「完了で終わらせず、復習イベントとして再配置」するタスク管理アプリである。

ユーザーはタスクを追加し、実施（クリア）後に「完了操作」を行う。アプリは完了履歴（復習履歴）に基づいて次回復習時刻を計算し、待機（スケジュール）として登録する。復習時刻を過ぎると復習待ちタスクとして再提示され、このサイクルを繰り返す。

## 2. 用語

- **タスク**: ユーザーが管理したい行動単位（例: 単語100個、章末問題、筋トレメニュー等）。
- **復習（Review）**: タスクの再実施。アプリ上は「復習待ち」になったタスクを実行し、完了操作を行うこと。
- **完了イベント（Completion Event）**: ユーザーが完了操作を押した時刻として記録される履歴データ。
- **復習回数（Review Count）**: 対象タスクに紐づく完了イベント数。
- **待ちタスク（Scheduled / Waiting）**: 次回復習時刻が未来にセットされており、まだ提示されないタスク。
- **復習待ちタスク（Due）**: 次回復習時刻を過ぎており、ユーザーに提示されるタスク。

## 3. アプリの流れ（ユーザー体験）

### 3.1 タスク追加

1. ユーザーがタスクを追加する。
2. 追加直後のタスクは、初回実施のため「今すぐ（Due）」として表示される。

### 3.2 タスク実施 → 完了操作

1. ユーザーがタスクを実行する。
2. 実行後、ユーザーがアプリ上で「タスク完了」操作を行う。
3. アプリは完了イベントを記録し、現在の復習回数（履歴の長さ）に基づいて次回復習時刻を計算する。
4. タスクは「待ちタスク」として再配置される（次回復習時刻まで表示されない）。

### 3.3 復習インターバル経過 → 復習待ちとして再提示

1. 復習インターバル（= 次回復習時刻までの残り時間）が経過すると、タスクは「復習待ち（Due）」へ状態遷移する。
2. ユーザーは再度タスクを実行し、完了操作を行う。
3. 3.2〜3.3を繰り返す。

## 4. 機能要件

### 4.1 タスク管理

- タスクを作成できる。
- タスクを編集できる（タイトル、メモ、タグ、優先度など）。
- タスクをアーカイブ/削除できる。
- タスク一覧を状態別に表示できる。
	- Due（復習待ち）
	- Waiting（待ち）
	- Archived（アーカイブ）

### 4.2 完了操作

- ユーザーはタスクに対して完了操作を行える。
- 完了操作により、完了イベント（timestamp）が履歴に追加される。
- 完了操作後、次回復習時刻が計算され、タスクはWaitingへ遷移する。

補足（復習評価）:

- 完了操作時に、ユーザーは復習評価を選択できる:
	- `again` / `hard` / `good` / `easy`
- 評価は次回復習インターバルの決定に影響する（6章・14章参照）。

### 4.3 復習スケジューリング（エビングハウス忘却曲線）

- タスクの完了履歴（時刻列）を入力として、次回復習時刻を算出する。
- 算出には、下記「復習インターバル計算ロジック」を使用する。

### 4.4 Due判定

- 現在時刻 $now$ において、$next\_review\_at \le now$ のタスクはDueとする。
- $next\_review\_at > now$ のタスクはWaitingとする。

### 4.6 設定（目標日数・テーマ）

- ユーザーは「記憶時間の目標日数（= horizon days / $T_{target}$ のオフセット）」を変更できる。
	- 初期値は **365日（1年）** とする。
	- 変更は **今後の完了から適用**する（既存 waiting の next_review_at は即時には変更しない）。
	- 設定画面から **「全タスク再計算」アクション**を実行できる（ボタンは置かず、メニュー/コンテキスト/ショートカットで起動する）。
- ユーザーは表示テーマを切り替えできる。
	- ライトモード / ダークモード
	- テーマに応じて、アプリ画面全体の背景画像を切り替える（15.1.6.2）。

### 4.7 復習の早期終了（ユーザー判断による除外）

- 復習待ちキュー（Due）および復習インターバル中（Waiting）のタスクについて、
	ユーザーが「十分に復習できた」と判断した場合、それ以降の復習サイクルから除外できる。
- 本仕様では、データは**論理削除**とし、アーカイブは復元可能とする。
	- アーカイブ済みはDue化（復習サイクル）対象から外す。
	- 終了理由の記録は行わない。

用語の整理:

- **アーカイブ**: 論理削除（復元可能）
- **削除**: UI文言として「削除」を出す場合でも、内部は論理削除で統一する

## 5. データ要件（概念モデル）

### 5.1 Task

- id: UUID
- title: string
- note: string（空可）
- status: enum { due, waiting, archived }
- created_at: datetime
- updated_at: datetime
- next_review_at: datetime（Due/Waiting判定の基準）

補足:

- 完了イベントの時刻列（history_times）と復習回数（review_count）は `completion_events` から導出する（保持しない）。


### 5.2 CompletionEvent（正規化して保持する）

- id: UUID
- task_id: UUID
- completed_at: datetime

本仕様の実装では、DB要件（13章）に従い `completion_events` に正規化して保持する。

## 6. 復習インターバル計算ロジック

本仕様は、ユーザー提示の計算式（ACT-R風 base activation と想起確率）に従う。

### 6.1 パラメータ（チューニング可能定数）

- $d$: decay（忘却の減衰係数）
	- 既定値: 0.5
- $s$: noise（シグモイドのなだらかさ）
	- 既定値: 0.4
- $\tau$: retrieval threshold（想起の閾値）
	- 既定値: 0.0
- $p_{target}$: 目標時点で保証したい想起確率
	- 既定値: 0.90
- $T_{target}$: 想起確率を保証したい目標の評価時点
	- 既定値: $now + 365$ days
	- **horizon days（目標日数）**はユーザー設定で変更可能（初期365日）

追加仕様（固定）:

- horizon_days の初期値: 365
- horizon_days の最大値: 365（1年のままでOK）

**時間単位**

- 計算は「日」を基準にする。
- $(eval\_time - t_k)$ は秒差を取り、$86400$ で割って日へ正規化する。

### 6.2 Base Activation

履歴時刻列 $history\_times = [t_1, t_2, ..., t_n]$ と評価時刻 $t$ に対し、

$$
B(t) = \ln\left(\sum_{k=1}^{n}{\left(\frac{t - t_k}{1\ \text{day}}\right)^{-d}}\right)
$$

と定義する。

### 6.3 想起確率

活性 $B$ から想起確率 $P$ を

$$
P = \frac{1}{1 + \exp\left(-\frac{B - \tau}{s}\right)}
$$

で計算する。

### 6.4 次回復習時刻の探索（find_next_review）

目的:

- $t_{next} \ge now$ を選び、履歴に $t_{next}$ を追加したと仮定した上で、
- 評価時刻 $T_{target}$ における想起確率 $P(T_{target}) \ge p_{target}$ を満たす
- **最小の** $t_{next}$ を返す

探索方法:

- $\Delta$ 日（nowからの経過日数）を二分探索する。
- 探索範囲: $[0, 365]$ days（最大は1年）
- 反復回数: 40 回（固定）

追加仕様（最小インターバル）:

- 最小インターバルは **1分** とする。
- `candidate_time` は必ず $now + 1$ minute 以上になるよう下限を適用する。

擬似コード（仕様準拠）:

```python
# 定数（チューニング可能）
d = 0.5      # decay
s = 0.4      # noise
tau = 0.0    # retrieval threshold (初期)
p_target = 0.90
T_target = now + 365 days

# helper: compute B given history times (list of timestamps) at eval_time t
def base_activation(history_times, eval_time, d):
		return log(sum(((eval_time - t_k).total_seconds()/86400.0)**(-d) for t_k in history_times))

# helper: probability from activation
def recall_prob(B, tau, s):
		return 1.0 / (1.0 + exp(-(B - tau)/s))

# goal: find next_review_time t_next (>= now) such that
# if we add event at t_next, the predicted P at T_target >= p_target
# (solve for minimal t_next satisfying that)

def find_next_review(history_times, now, d, tau, s, p_target, T_target):
		# We'll search Δ days from now in [min_gap, max_gap]
		lo = 0.0   # days
		hi = 365.0 # cap max search
		for iter in range(40):
				mid = (lo + hi)/2
				candidate_time = now + mid days
				# new_history = history_times + [candidate_time]
				B_future = base_activation(history_times + [candidate_time], T_target, d)
				p = recall_prob(B_future, tau, s)
				if p >= p_target:
						hi = mid
				else:
						lo = mid
		return now + hi days
```

### 6.5 実装上の注意（仕様）

- **history_times が空の場合**
	- 追加直後で履歴がないタスクは「Due」として扱う（初回はすぐ実施）。
	- find_next_review は history_times が空でも動作するようにするか、仕様として「完了後にのみ呼ぶ」とする。
		- 本仕様では「完了後にのみ呼ぶ」を基本とする（完了後は少なくとも1件履歴があるため）。

- **$eval\_time - t_k$ が 0 になるケース**
	- 同一時刻に複数イベントが入ると $(0)^{-d}$ が発散する。
	- 本仕様では、**最小インターバル（1分）を適用**することで回避する。
		- 例: 直前の completed_at と now が同一（または近すぎる）場合、記録時刻を `last_completed_at + 60秒` に繰り上げる
		- もしくは、base_activation 側で `delta_days = max(delta_days, 60/86400)` の下限を持つ

- **時間丸め**
	- next_review_at は分単位に切り上げて丸める。
	- 丸めは一方向（未来側）にのみ行う（Due判定の正当性を崩さない）。

## 7. 状態遷移

### 7.1 状態

- due: ユーザーに提示すべき
- waiting: 次回復習時刻まで待機
- archived: 対象外

### 7.2 遷移

- 追加: (new) → due
- 完了操作:
	- due → waiting（next_review_at を計算して設定）
- 時刻経過:
	- waiting → due（next_review_at <= now になった時）
- アーカイブ:
	- due/waiting → archived

## 8. 画面要件（最小）

### 8.1 ホーム（一覧）

- Dueタスク一覧（優先表示）
- Waitingタスク一覧（次回復習時刻つき）

### 8.2 タスク詳細

- タイトル、メモ、タグ
- 復習回数（= 履歴件数）
- 次回復習時刻 next_review_at
- 完了操作（ボタンは置かない。キー操作/コンテキストメニューで実行）
- 履歴一覧（timestampの列）

### 8.3 タスク作成/編集

- title（必須）
- note（空可）

## 9. 非機能要件

- 時刻は UTC の epoch seconds（INTEGER）で保存し、UI表示はローカルタイムへ変換して表示する。
- 計算結果は再現可能であること（同じ履歴・同じパラメータなら同じ next_review_at）。
- ローカルストレージ/DBのいずれでも、履歴の欠損が起きないようにする。

## 10. 受け入れ基準（確認事項）

- タスクを追加するとDue一覧に出る。
- Dueタスクに完了操作をすると、履歴が1件追加され、Waitingへ移動する。
- Waitingタスクは next_review_at までDueに出ない。
- next_review_at を過ぎるとDueに戻る。
- find_next_review の計算が仕様（6章）と一致する（パラメータ含む）。

## 11. 技術スタック要件（確定）

### 11.1 GUI

- Python + **PySide6 (Qt for Python)** を使用する。
- UIは **Qt Quick（QML）** で実装する。
- UIの記述は **QMLファイル** で行う（Pythonコードでウィジェットを組まない）。
- PythonはQMLをロードし、QMLへ以下を公開する:
	- 一覧表示用のモデル（Due/Waiting/Archived）
	- 操作コマンド（完了/アーカイブ/復元/purge/検索/設定変更）

### 11.0 開発環境（venv）

- 本プロジェクトは **venv（Python仮想環境）** 上で開発する。
- 仮想環境のディレクトリは以下を使用する:
	- `/home/yakisenbei/Documents/YakiSuperTaskMaster/bin/`
		- 例: `python`, `pip`, `activate` が配置されていること

#### 11.0.1 前提

- venvに入っているPythonで実行・依存導入を行う。
- `pip` は venv のものを使用する（システムPythonの `pip` は使わない）。

#### 11.0.2 開発時の基本手順（参考）

※ 実装時に README にも同等の内容を記載する。

```bash
# venv有効化
source /home/yakisenbei/Documents/YakiSuperTaskMaster/bin/activate

# 依存導入（例）
pip install -U pip
pip install pyside6
```

### 11.2 DB / SQL

- 永続化は **SQLデータベース** を使用する。
- 永続化は **SQLite** を使用する。
- Python DBアクセスは `sqlite3`（標準） + 手書きSQLで実装する。

本仕様書のDDL例はSQLite互換を基本とする。

## 12. アーキテクチャ

### 12.1 レイヤ構成

- **UI層（QML + PySide6）**
	- 画面/ダイアログはQMLファイルで定義し、ユーザー操作を受ける
	- PythonはUIの状態・モデル・コマンドを提供する
- **アプリケーション層（UseCase/Service）**
	- 完了操作、次回復習計算、状態遷移、Due更新などの業務ロジック
- **ドメイン層（Model）**
	- Task、ReviewParams 等のデータ構造（純粋Python）
- **インフラ層（Repository/DAO）**
	- SQL発行、トランザクション、マイグレーション

### 12.2 時刻の取り扱い（実装規約）

- DB保存は **UTC** を基本とする。
- Python内部は `datetime`（timezone-aware）を基本とする。
- DBのDATETIMEは **INTEGER（Unix epoch seconds, UTC）** に統一する（混在禁止）。

## 13. DB設計（SQLスキーマ）

### 13.1 方針

- `history_times` を配列で持つのではなく、**CompletionEventとして正規化**して保持する。
	- 理由: SQLでの集計・参照・監査が容易、データ破損しにくい。
- Taskは `next_review_at` をキャッシュとして保持する（Due判定高速化）。

### 13.2 テーブル一覧

- `tasks`: タスク本体
- `completion_events`: 完了（復習）イベント（時系列ログ）

追加:

- `task_tags`: タグのマスタ
- `task_tag_map`: タスクとタグの中間
- `schema_version`: スキーマバージョン管理

### 13.3 DDL（SQLite互換の例）

```sql
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS tasks (
	id               TEXT PRIMARY KEY,              -- UUIDを文字列で保持
	title            TEXT NOT NULL,
	note             TEXT NOT NULL DEFAULT '',
	status           TEXT NOT NULL,                 -- 'due' | 'waiting' | 'archived'
	created_at       INTEGER NOT NULL,              -- epoch seconds (UTC)
	updated_at       INTEGER NOT NULL,              -- epoch seconds (UTC)
	next_review_at   INTEGER,                       -- epoch seconds (UTC), NULL可

	deleted_at       INTEGER,                       -- 論理削除（NULLなら有効）
	purged_at        INTEGER,                       -- 完全な論理削除（復元不可、NULLなら未purge）

	CHECK (status IN ('due', 'waiting', 'archived'))
);

CREATE TABLE IF NOT EXISTS completion_events (
	id            TEXT PRIMARY KEY,                 -- UUID
	task_id       TEXT NOT NULL,
	completed_at  INTEGER NOT NULL,                 -- epoch seconds (UTC)

	grade         TEXT NOT NULL,                    -- 'again' | 'hard' | 'good' | 'easy'

	FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

	CREATE TABLE IF NOT EXISTS task_tags (
		id         TEXT PRIMARY KEY,                    -- UUID
		name       TEXT NOT NULL UNIQUE,
		created_at INTEGER NOT NULL
	);

	CREATE TABLE IF NOT EXISTS task_tag_map (
		task_id TEXT NOT NULL,
		tag_id  TEXT NOT NULL,
		PRIMARY KEY(task_id, tag_id),
		FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE,
		FOREIGN KEY(tag_id)  REFERENCES task_tags(id) ON DELETE CASCADE
	);

	CREATE TABLE IF NOT EXISTS schema_version (
		version INTEGER NOT NULL
	);

CREATE INDEX IF NOT EXISTS idx_tasks_status_next_review
	ON tasks(status, next_review_at);

CREATE INDEX IF NOT EXISTS idx_tasks_deleted
	ON tasks(deleted_at);

CREATE INDEX IF NOT EXISTS idx_completion_events_task_time
	ON completion_events(task_id, completed_at);

CREATE INDEX IF NOT EXISTS idx_completion_events_task_grade_time
	ON completion_events(task_id, grade, completed_at);

CREATE INDEX IF NOT EXISTS idx_tag_map_tag
	ON task_tag_map(tag_id);

CREATE INDEX IF NOT EXISTS idx_tag_map_task
	ON task_tag_map(task_id);
```

### 13.4 SQLの型について（SQLiteと一般SQLの対応）

SQLiteは動的型付け（Type Affinity）だが、他RDBへ移行しやすいよう **論理型** を定義する。

SQLiteは動的型付け（Type Affinity）だが、本仕様では可読性のため **論理型** を定義する。

#### 13.4.1 論理型 → SQLite型

- **UUID**
	- 論理型: UUID
	- SQLite: `TEXT`（例: `"550e8400-e29b-41d4-a716-446655440000"`）

- **文字列**
	- 論理型: string
	- SQLite: `TEXT`

- **真偽**
	- 論理型: boolean
	- SQLite: `INTEGER`（0/1）

- **整数**
	- 論理型: int
	- SQLite: `INTEGER`

- **浮動小数**
	- 論理型: float
	- SQLite: `REAL`

- **日時（UTC）**
	- 論理型: datetime
	- SQLite: `INTEGER`（epoch seconds）

- **列挙**
	- 論理型: enum
	- SQLite: `TEXT` + `CHECK(...)`

#### 13.4.2 Python（PySide6）での型変換ルール

- DB保存/比較のため、`datetime` は epoch seconds（int）へ変換して保存する。
- UI表示はローカルタイムへ変換して表示する。
- 精度は分単位を基本とし、分への切り上げ丸めは保存前に行う（6.5参照）。

## 14. 主要ユースケース（CRUD + 完了）

### 14.1 タスク作成

入力:

- title（必須）
- note（空可）

処理:

- `tasks` にINSERT
- status は `due`
- `next_review_at` は NULL または now（実装統一）

出力:

- 作成されたTask

### 14.2 タスク完了（最重要）

入力:

- task_id
- completed_at（通常は now）
- grade（`again/hard/good/easy`）

処理（トランザクション必須）:

0. 最小インターバル（1分）を満たすよう completed_at を必要に応じて繰り上げる
1. `completion_events` にINSERT（完了イベント追加。gradeも保存）
2. 当該タスクの `completion_events.completed_at` を時刻昇順で取得し `history_times` を構築
3. grade に応じてパラメータ（例: $p_{target}$ 等）を動的に決定し、6章の `find_next_review(...)` で `next_review_at` を計算
4. `tasks.status = 'waiting'`、`tasks.next_review_at = 計算結果`、`updated_at = now` をUPDATE

出力:

- 次回復習時刻 next_review_at

#### 14.2.1 grade による動的決定（仕様）

grade により次回復習を「より早く/遅く」調整する。

本仕様では、実装依存を最小にするため **p_target を grade により変化**させる方式を採用する。

- again: p_target = 0.98（かなり忘れやすい前提で早めに復習）
- hard:  p_target = 0.95
- good:  p_target = 0.90（標準）
- easy:  p_target = 0.85（維持できそうなら間隔を伸ばす）

※ これらの値はチューニング可能。UI設定で上書きできてもよいが、まずは固定でよい。

### 14.3 Due更新（定期評価）

目的:

- `waiting` タスクのうち `next_review_at <= now` のものを `due` にする。

処理（例）:

```sql
UPDATE tasks
SET status = 'due', updated_at = :now
WHERE status = 'waiting'
	AND next_review_at IS NOT NULL
	AND next_review_at <= :now;
```

実行タイミング（固定）:

- アプリ起動時に1回
- 一覧表示の更新タイミング
- `QTimer` で1分ごとに実行

### 14.4 タスクのアーカイブ（論理削除）

目的:

- 「十分に復習できた」判断で、復習サイクル対象から外す（復元可能）。

処理:

- `tasks.deleted_at = now` をセット
- `tasks.status = 'archived'` をセットする

```sql
UPDATE tasks
SET deleted_at = :now,
		status = 'archived',
		updated_at = :now
WHERE id = :task_id;
```

### 14.5 タスクの復元

```sql
UPDATE tasks
SET deleted_at = NULL,
		status = CASE
			WHEN next_review_at IS NOT NULL AND next_review_at <= :now THEN 'due'
			ELSE 'waiting'
		END,
		updated_at = :now
WHERE id = :task_id;
```

## 15.5 検索（DBベース・ビュー別）

- 検索対象は title と note の両方とする。
- 検索はインクリメンタル検索（15.1.2）であり、絞り込みはDBクエリで実行する（15.1.2.3）。
- 検索の適用範囲は「現在表示中のビュー」に従う。
	- Due/Waiting: `deleted_at IS NULL AND purged_at IS NULL AND status IN ('due','waiting')`
	- Archived: `deleted_at IS NOT NULL AND purged_at IS NULL AND status = 'archived'`
- title/note 部分は SQLite の `LIKE` による部分一致を最小実装とする。
- `#タグ` を含む場合はタグ条件をANDで結合する（20.3）。

SQL例は 22.3 / 22.4 / 22.4.1 を参照する。

## 15.6 キュー（2種類）とソート

一覧は以下の2キューを持つ:

- **復習待ちキュー（Due）**: `status='due'` かつ `deleted_at IS NULL`
	- ソート: **古い順**（主に `next_review_at` 昇順、NULLは末尾）
- **インターバル待ちキュー（Waiting）**: `status='waiting'` かつ `deleted_at IS NULL`
	- ソート: **新しい順**（主に `next_review_at` 降順、NULLは末尾）

※ UIでソートの切替（昇順/降順）は提供しない。デフォルトは上記で固定する。

## 15. 画面要件（PySide6前提の詳細）

### 15.0 UI思想（ボタンレス設計）

本アプリのUI思想は「ボタンを使わない設計」とする。

定義（本仕様における「ボタン」）:

- 画面内に常時配置されるクリック前提のアクションUI（例: `Button` / `ToolButton` / ツールバーの押下ボタン）。

許容する導線（ボタンレスを満たす）:

- メニューバー（`MenuBar`）のアクション
- コンテキストメニュー（右クリック/二本指タップ相当）
- キーボードショートカット（最優先の導線）
- ダブルクリック/Enter などの標準ジェスチャ
- インライン編集（`TableView` の編集、`Dialog` 内の入力確定をキー操作で行う）
- ステータスバー（ショートカットのヒント表示）

許容する常設UI（ボタンレス設計と矛盾しないもの）:

- 入力/選択のためのコントロール（例: `TextField`, `ComboBox`）
	- ただし「アクションを実行するための押下ボタン」は置かない

※ 目的は「UI上のボタンを探して押す」コストをゼロにし、視線移動と意思決定コストを最小化すること。

### 15.1 メインウィンドウ

UI方針:

- 画面上にアクション用ボタンを置かない（15.0参照）。
- 主要導線は「キーボード操作 + 最小の入力（検索/コマンド）」に寄せる。
- 右クリック（コンテキストメニュー）を第二導線とする。
- 角が立たない **柔らかな形状**（角丸、余白広め、控えめな枠線）を採用する。
- ダークモード時の配色は 15.1.6.1 に従い、グレー系を基調として黒をそのまま使う等の強い色を使わない。

#### 15.1.0 レイアウト（ヘッダー + 左サイドバー + メイン）

画面は以下の3領域で構成する。

1) ヘッダー（上部）

- メニューバー（`MenuBar`）を常時表示する。
- ヘッダー右側に状態表示領域を置く（固定仕様は 15.1.2.0 を参照）。

2) 左サイドバー（ナビゲーション）

- 表示切替のためのナビゲーションバーを左に固定表示する。
- 項目（最小）:
	- Due
	- Waiting
	- Archived
	- Settings

3) メインコンテンツ

- 左サイドバーで選択されたコンテンツを表示する。
- 実装例: `StackLayout` でビューを切替。

※ 実装上は `ApplicationWindow` をルートにし、上部に `MenuBar`、中央に「左サイドバー + メイン」を配置する（UIはQMLで記述する）。

#### 15.1.1 画面切替（サイドバー）

- サイドバー選択でビューを切替する。
- キーボードでも切替できること:
	- Ctrl+1: Due
	- Ctrl+2: Waiting
	- Ctrl+3: Archived
	- Ctrl+4: Settings

表示内容（一覧は `TableView`）:

- Due: タイトル、最終完了時刻、復習回数、次回復習時刻
- Waiting: タイトル、次回復習時刻（ローカル表示）、残り時間、復習回数
- Archived: タイトル、アーカイブ時刻（= deleted_at）、最終完了時刻、復習回数
- Settings: 設定項目一覧（horizon_days, theme, DBパス等）

#### 15.1.1.1 左サイドバーの仕様（固定）

目的:

- 画面切替を「常設のナビゲーション」に集約し、ボタンレス設計でも迷いなく遷移できるようにする。

構成:

- 実装は `ListView` とする（フラットなリスト）。
- 項目順は固定とする:
	1. Due
	2. Waiting
	3. Archived
	4. Settings

見た目:

- 幅: 220px（固定）。
- ラベル: 項目名は短く固定（`Due`, `Waiting`, `Archived`, `Settings`）。

バッジ（情報量・固定）:

- Due と Waiting には件数バッジを表示する。
	- Due: `status='due' AND deleted_at IS NULL AND purged_at IS NULL` の件数
	- Waiting: `status='waiting' AND deleted_at IS NULL AND purged_at IS NULL` の件数
- Archived は件数バッジを表示しない。
- Settings はバッジを表示しない。

選択・フォーカス:

- 現在表示中のビューは、サイドバーで選択状態として強調表示する。
- キーボードフォーカスがサイドバーにある場合は、フォーカスリング/ハイライトを表示する（アクセシビリティ）。
- サイドバー項目の選択変更で、即座にビューを切替する（確認ダイアログ等は不要）。

操作:

- マウス: クリックで切替（ボタンではなくリスト選択として扱う）。
- キーボード:
	- ↑/↓: 項目移動
	- Enter: 選択項目へ切替
	- Ctrl+1..4: 直接切替（15.1.1）

#### 15.1.2 ヘッダー（検索・表示）

- 検索欄はヘッダーに配置する。
	- 入力フォーカス: Ctrl+F
	- 検索はインクリメンタル検索とする（入力に追従してフィルタ適用）。
	- 解除: Esc（入力クリア + フィルタ解除）
	- Enter: Focus List（検索確定には使用しない）
- 検索は以下の両方に対応する（15.5, 20.3と整合）:
	- title/note 検索
	- `#タグ` 検索（複数はAND、残り文字列はtitle/note検索とAND）

#### 15.1.2.3 インクリメンタル検索の仕様（固定）

適用範囲:

- 検索は「現在表示中のビュー」に対して適用する（Due/Waiting/Archived）。
- Settingsビューは検索対象外とする。

適用タイミング:

- 入力文字列が変化したら自動でフィルタを更新する。
- DBへの問い合わせが発生する場合はデバウンスを入れる（既定: 150ms、実装で調整可）。

実装方針（固定）:

- インクリメンタル検索の絞り込みはDBクエリで実行する（一覧全件をメモリに読み込んでフィルタする方式は採用しない）。
	- 理由: 件数増加時のパフォーマンスと、DBを正とした一貫性を優先する。
	- 実装は「デバウンス後にクエリ再実行→モデル差し替え」を基本とする。

クエリ戦略（最小）:

- title/note 部分は 15.5 の `LIKE` を用いた部分一致を最小実装とする。
- `#タグ` 条件は 22.4 / 22.4.1 のAND検索を使用する。
- title/note 条件とタグ条件は AND で結合する（20.3と整合）。

クエリ解釈（確定）:

- クエリ文字列中の `#` から始まるトークンをタグ指定として抽出する。
	- 例: `grammar #english #toeic` → title/noteに`grammar` AND tagに`english` AND tagに`toeic`
	- タグは 20.2 の正規化（空白縮約+小文字化）を適用して比較する。
- `#` を含まない残りの文字列は title/note 検索として扱う。
- クエリが空（空白のみ含む）になった場合はフィルタを解除し、全件表示に戻す。

表示・UX:

- フィルタの結果が0件の場合は、一覧の空状態とは別に「検索結果0件」を表示する。

選択維持:

- フィルタ更新で現在の選択行が残る場合は選択を維持する。
- 選択行が消えた場合は、先頭行を選択する（結果が0件なら未選択）。

#### 15.1.2.0 ヘッダー右側の表示領域（固定）

ヘッダーは「左（タイトル/コンテキスト）・中央（検索）・右（状態表示）」の3ゾーンで構成する。

右側の表示領域は、原則として「状態の可視化」に徹し、クリック前提のボタンUIを置かない。

表示項目（固定）:


- Theme: `light | dark` の現在値を表示する。
	- 変更操作は View→Theme または Settings から行えること（ボタンレス）。
- DB: 現在使用中のDBファイルの情報を表示する。
	- 表示はファイル名のみ（例: `taskmaster.db`）とする。
	- DBが未設定/未作成の場合は `DB: (not set)` を表示する。

ツールチップ（固定）:

- Theme: 切替方法のヒント（例: `View → Theme`）
- DB: フルパス、schema_version

表示ルール:

- 右側領域は1行に収め、長い文字列は省略表示（エリプシス）し、ツールチップで補完する。
- 右側領域のクリックは「表示」用途に留め、操作の起点にしない（ボタンレス原則）。

#### 15.1.2.1 フォーカスと遷移（必須）

フォーカスの基本ルール:

- 起動直後の初期ビューは Due とする。
- 起動直後はメインコンテンツ（一覧）にフォーカスを置く。
- サイドバー切替後も、原則としてメインコンテンツにフォーカスを戻す（連続レビュー操作を優先）。

フォーカス移動（必須）:

- Focus Sidebar（例: Alt+1 または View→Focus Sidebar）
- Focus Search（例: Ctrl+F または View→Focus Search）
- Focus List（例: Esc または View→Focus List）

選択状態:

- ビュー切替時、直前の選択行（task_id）が当該ビューに存在する場合は復元する。存在しない場合は先頭行を選択する（0件なら未選択）。
- 検索フィルタ適用/解除時、選択行が結果に残る場合は選択を維持する。消えた場合は先頭行を選択する（0件なら未選択）。

#### 15.1.2.2 メインコンテンツ（ビュー別仕様・必須）

メインコンテンツはビューごとに以下の表示/動作を満たす。

共通（Due/Waiting/Archived）:

- 一覧は `TableView`（モデル/ビュー分離）で実装する。
- 行はタスクを表し、主キーは `tasks.id` とする。
- 既定ソートは仕様 15.6 および 22章に従う。
- 行ダブルクリック/Enterで詳細を開く。

##### 15.1.2.2.1 Dueビュー（復習待ち）

表示:

- 列（最小）:
	- Title
	- Last Completed（ローカル表示、無ければ空）
	- Review Count
	- Next Review At（ローカル表示、Dueなので通常は過去/現在。NULLは末尾）
	- Tags
- ソート: 22.1（古い順、NULL末尾）

操作:

- 完了: Ctrl+S（`good`）
- grade指定完了: 1..4（again/hard/good/easy）
- アーカイブ: Delete

空状態（Dueが0件）:

- メインに「Dueは0件。Waitingを確認するか、新規タスクを追加してください。」等、次の行動が分かるメッセージを表示する。

##### 15.1.2.2.2 Waitingビュー（インターバル待ち）

表示:

- 列（最小）:
	- Title
	- Next Review At（ローカル表示）
	- Remaining（残り時間。例: `3h 12m` / `2d 5h`）
	- Review Count
	- Tags
- ソート: 22.2（新しい順、NULL末尾）

操作:

- 完了操作は原則無効（誤操作防止）。
	- 右クリックメニューやショートカットからの完了も無効化し、ステータスバーに理由を表示する。
- アーカイブ: Delete

空状態（Waitingが0件）:

- メインに「Waitingは0件。Dueのタスクを完了するとここに移動します。」等のメッセージを表示する。

##### 15.1.2.2.3 Archivedビュー（アーカイブ）

表示:

- 列（最小）:
	- Title
	- Archived At（= deleted_at のローカル表示）
	- Last Completed
	- Review Count
	- Tags
- ソート: `deleted_at` 降順（新しいアーカイブが上）を既定とする。

操作:

- 復元: Ctrl+R（deleted_atをNULL、statusは14.5のCASEで復元）
- 完全削除（復元不可）: Shift+Delete（19章のpurged_atをセット）

空状態:

- 「アーカイブは0件」表示。

##### 15.1.2.2.4 Settingsビュー（設定）

表示:

- セクション（最小）:
	- General: horizon_days, theme
	- Storage: DBファイルパス、マイグレーション、バックアップ

操作（ボタンレス）:

- 設定値の編集はインライン編集または詳細ダイアログで行う。
- アクションの起動はメニュー/ショートカット/コンテキストメニューから行う。
	- Run Migration…（DB選択→確認→実行）
	- Backup…（保存先選択→確認→実行）
	- Recalculate All Tasks…（21章）

空状態:

- 常に表示（空状態なし）。

#### 15.1.3 メニューバー（必須）
メニューバーの構成例（最小）:

- Task
	- New Task…
	- Edit…
	- Complete (Good)
	- Complete As…（grade選択）
	- Archive
	- Restore（Archived表示時）
	- Purge（Archived表示時、危険操作）
- View
	- Go To → Due / Waiting / Archived / Settings
	- Focus Sidebar
	- Focus Search
	- Focus List
	- Refresh（Due更新含む）
	- Theme（Light/Dark）
- Settings
	- Preferences…（horizon_days、DB、再計算、バックアップ等）

#### 15.1.4 一覧の操作体系（必須）

一覧（`TableView`）上での基本操作:

- 行選択: ↑/↓（複数選択はShift/Control）
- 詳細を開く: Enter またはダブルクリック
- 編集: F2 または Enter（詳細画面内の編集）
- 検索へフォーカス: Ctrl+F
- 更新: F5（Due更新を含む）

コンテキストメニュー（行上の右クリック）はビューにより内容が変わる。

Dueビュー（行上）:

- Open Details
- Edit…
- Complete (Good)
- Complete As → again / hard / good / easy
- Archive
- Copy Title

Waitingビュー（行上）:

- Open Details
- Edit…
- Archive
- Copy Title

Archivedビュー（行上）:

- Open Details
- Restore
- Purge（危険）
- Copy Title

空白部のコンテキストメニュー:

- New Task…（Due/Waitingのみ表示）
- Refresh

#### 15.1.5 ショートカット（既定案・実装で上書き可）

- New Task: Ctrl+N
- Open Details: Enter
- Edit Task: F2
- Complete (Good): Ctrl+S（Due/詳細画面で有効）
- Complete As: 1=again / 2=hard / 3=good / 4=easy
- Archive: Delete
- Restore（Archived）: Ctrl+R
- Purge（Archived, 危険）: Shift+Delete
- Search: Ctrl+F
- Refresh: F5
- Preferences: Ctrl+,
- Switch View: Ctrl+1..4（15.1.1参照）

### 15.1.6 テーマ切り替え（ライト/ダーク）

- メニューまたは設定画面からライト/ダークを切り替える。
- テーマは QML 側で適用する（例: `QtQuick.Controls.Material` の `Material.theme` を切り替える）。
- テーマ切替は即時反映（アプリ再起動不要）とする。

追加仕様（背景画像 + 透過UI）:

- テーマに応じて、アプリ画面全体の背景画像を切り替える（15.1.6.2）。
- ヘッダー/サイドバー/テーブル/ダイアログ等のUI面は、背景画像が透ける一定の透過度を持つ（15.1.6.1）。

背景画像のパス :

- ダークテーマの場合:/home/yakisenbei/Pictures/YakiSuperTaskMaster/theme/dark.png
- ライトテーマの場合:/home/yakisenbei/Pictures/YakiSuperTaskMaster/theme/light.png

### 15.1.6.1 配色・透過（固定）

本アプリは、画面全体の背景にテーマ別の背景画像を表示し（15.1.6.2）、その上に半透明のUI面（サーフェス）を重ねる。

基本方針（固定）:

- 背景画像の上でも可読性を確保するため、UI面（ヘッダー/サイドバー/テーブル/ダイアログ）の背景は半透明とする。
- 高彩度の強い色を面積の大きい要素（面/選択強調）に使わない。
- エラー/危険は背景全面を赤くする等の強い表現は行わない（文言 + アイコン + 小さな色面で示す）。

パレット（固定・HEX）:

- Surface: `#252526`
- Surface Elevated: `#2D2D30`
- Separator / Border: `#3C3C3C`
- Text Primary: `#E6E6E6`
- Text Secondary: `#BDBDBD`
- Text Disabled: `#7A7A7A`
- Selection Background: `#3A3D41`
- Accent: `#6CA0DC`
- Danger: `#D16969`

透過度（固定）:

- Surface Opacity: `0.82`
- Surface Elevated Opacity: `0.88`

適用ルール（固定）:

- 主要なUI面（ヘッダー、サイドバー、一覧の背景、詳細/編集ダイアログの面）には、上記の `Surface` / `Surface Elevated` と透過度を適用する。
	- 例: `Surface` を `rgba(Surface, Surface Opacity)` として使用する（実装はQML側で統一）。
- 罫線・区切りは Separator / Border を使用し、コントラストを強くしすぎない。
- 選択状態は Selection Background を用いるが、面積の大きいベタ塗りは避け、行ハイライト等の限定的な面積に留める。

補足（フォールバック）:

- 背景画像が読み込めない場合に備え、背景色のフォールバックとして `#1E1E1E` を使用してよい（あくまでフォールバック）。

### 15.1.6.2 背景画像（固定）

テーマ別の背景画像を、アプリ画面全体の背景として表示する。

背景画像の配置場所（固定）:

- ダークテーマ: `/home/yakisenbei/Pictures/YakiSuperTaskMaster/dark`
- ライトテーマ: `/home/yakisenbei/Pictures/YakiSuperTaskMaster/light`

画像の選択ルール（固定）:

- 各ディレクトリ直下の `background.png` を使用する。
- `background.png` が存在しない場合は、拡張子が `.png|.jpg|.jpeg|.webp` のファイルを名前順で探索し、最初の1枚を使用する。
- 画像が見つからない場合は、15.1.6.1 のフォールバック背景色を使用する。

表示ルール（固定）:

- 背景画像はウィンドウ全体に表示する。
- 画像の縦横比は維持し、必要に応じてトリミングして全面を埋める（例: PreserveAspectCrop 相当）。
- 背景画像はUIの操作対象ではない（クリック/選択/ドラッグ等の入力を受けない）。

### 15.2 タスク作成/編集ダイアログ

- `Dialog`（QML）
- title必須のバリデーション
- ボタンレス運用:
	- 確定: Ctrl+S
	- キャンセル: Esc
	- 画面上のOK/Cancelボタンは配置しない

### 15.3 タスク詳細

- 完了操作（ボタンは置かない）:
	- 既定: Ctrl+S = `good`
	- grade指定: 1=again / 2=hard / 3=good / 4=easy
	- 右クリック → Complete As… でも実行可能
- 履歴一覧（`completion_events` の completed_at）

追加操作:

- 「十分に復習できた」
	- 既定動作: アーカイブ

危険操作（完全削除）の確認仕様（ボタンレス）:

- 確認ダイアログは `Dialog`（QML）を用いる。
- ユーザーに確認テキスト（例: `purge`）の入力を要求し、Enterで確定、Escでキャンセル。

## 17. 設定の永続化（ユーザー設定）

### 17.1 設定項目

- horizon_days（記憶時間の目標日数）
	- 型: int
	- 初期値: 365
	- 制約: 1〜365
- theme
	- 型: enum { light, dark }
	- 初期値: light

### 17.2 保存先

- `QSettings` を使用してOS標準の設定ストアへ保存する。

## 18. DBファイル・マイグレーション・バックアップ

### 18.1 データ保存先

- DBファイルの既定保存ディレクトリは以下とする:
	- `/home/yakisenbei/.local/share/`

追加仕様:

- 指定されたDBファイルが存在しない場合、アプリが**自動作成**する。
- DBファイル名の制約は設けない。
- DB履歴保存は行わない。

### 18.2 schema_version とマイグレーション

- `schema_version` テーブルの `version` によりスキーマバージョンを管理する。
- マイグレーションは **設定画面からDBファイルを指定して実行**できるようにする。
	- 例: 「DBを選択」→「マイグレーション実行」
	- 誤操作防止のため確認ダイアログを必須とする。

### 18.3 バックアップ

- 自動バックアップは行わない。
- 設定画面からバックアップを作成できる。
- 本仕様では、バックアップは **単純コピー** とする。
	- コピー前にトランザクション中の処理がない状態にし、UIを一時的にロックする。

## 19. 論理削除・アーカイブの確定ルール

- `deleted_at IS NOT NULL` のタスクは、常にアーカイブ状態として扱う。
	- UI上のステータスは `archived` とする。
	- Due更新（14.3）やキュー（15.6）の対象外。
- アーカイブ（復元可能）:
	- `purged_at IS NULL` かつ `deleted_at IS NOT NULL`
- 完全な論理削除（復元不可）:
	- **すでにアーカイブ状態**のタスクを削除した場合、`purged_at` をセットする（物理削除はしない）。

## 20. UI仕様の追加（grade・タグ）

### 20.1 完了（grade）UI

ボタンレスのため、完了UIは「キー操作とコンテキストメニュー」を基本とする。

- 既定完了: Ctrl+S = `good`
- grade指定完了: 1=again / 2=hard / 3=good / 4=easy
- マウス導線: 行の右クリック → Complete As → again/hard/good/easy

補足:

- Due一覧・詳細画面のどちらからも完了操作を実行できる。
- Waiting一覧からの完了は原則無効（誤操作防止）。

### 20.2 タグ仕様

- タスクに付与できるタグ数の上限は **5**。
- タグ名は正規化して保持する（確定仕様）:
	- 前後空白を除去
	- 連続する空白（半角/全角）は1つに縮約
	- **小文字化して保存/比較する**（case-insensitiveを実装に頼らず、正規化で統一）
- 未使用タグの自動削除は行わない。

### 20.3 `#タグ` 検索

- 検索ボックス入力に `#` が含まれる場合、タグ検索として解釈する（確定仕様）。
	- `#a #b` のように複数指定された場合は **AND条件** とする。
	- `#` を含まない残りの部分は title/note 検索として扱い、タグ条件と **AND** で組み合わせる。
		- 例: `grammar #english` => (title/noteにgrammar) AND (tag=english)

## 21. 全タスク再計算（設定から実行）

目的:

- horizon_days 変更などに合わせて、`due` / `waiting` のタスクを一括で再スケジュールする。

対象:

- `deleted_at IS NULL` かつ status が `due` または `waiting`

計算ルール:

- 各タスクの `completion_events` を時刻昇順で取得して `history_times` を構築
- **最新の完了イベントの grade の p_target** を使用して `find_next_review` を実行
- 再計算結果を `tasks.next_review_at` に保存

実行中UI:

- 実行中はプログレスを表示する。

完了後:

- 全件計算後に Due更新（14.3）を実行する。

## 22. 主要SQL一覧（実装用）

この章のSQLはSQLite互換の例であり、`:` は名前付きパラメータを表す。

### 22.1 Due一覧（復習待ちキュー: 古い順）

```sql
SELECT t.*
FROM tasks t
WHERE t.deleted_at IS NULL
	AND t.purged_at IS NULL
	AND t.status = 'due'
ORDER BY
	CASE WHEN t.next_review_at IS NULL THEN 1 ELSE 0 END,  -- NULLは末尾（確定仕様）
	t.next_review_at ASC,
	t.updated_at ASC;
```

### 22.2 Waiting一覧（インターバル待ちキュー: 新しい順）

```sql
SELECT t.*
FROM tasks t
WHERE t.deleted_at IS NULL
	AND t.purged_at IS NULL
	AND t.status = 'waiting'
ORDER BY
	CASE WHEN t.next_review_at IS NULL THEN 1 ELSE 0 END,  -- NULLは末尾（確定仕様）
	t.next_review_at DESC,
	t.updated_at DESC;
```

### 22.3 title/note検索（Due/Waiting）

```sql
SELECT t.*
FROM tasks t
WHERE t.deleted_at IS NULL
	AND t.purged_at IS NULL
	AND t.status IN ('due', 'waiting')
	AND (t.title LIKE :q OR t.note LIKE :q)
ORDER BY t.updated_at DESC;
```

補足（Archivedビューでのtitle/note検索）:

- `WHERE` 句の基底条件を以下に置換する:
	- `t.deleted_at IS NOT NULL AND t.purged_at IS NULL AND t.status = 'archived'`

### 22.4 `#タグ` 検索（単一タグ・最小実装）

```sql
SELECT t.*
FROM tasks t
JOIN task_tag_map m ON m.task_id = t.id
JOIN task_tags g ON g.id = m.tag_id
WHERE t.deleted_at IS NULL
	AND t.purged_at IS NULL
	AND t.status IN ('due', 'waiting')
	AND g.name = :tag
ORDER BY t.updated_at DESC;
```

補足（Archivedビューでの`#タグ`検索）:

- `WHERE` 句の基底条件を以下に置換する:
	- `t.deleted_at IS NOT NULL AND t.purged_at IS NULL AND t.status = 'archived'`

### 22.4.1 `#タグ` AND検索（複数タグ）

タグを複数指定した場合は AND 条件とする。

例: `:tags_len = 2`、`:tag1='english'`、`:tag2='math'`

```sql
SELECT t.*
FROM tasks t
JOIN task_tag_map m ON m.task_id = t.id
JOIN task_tags g ON g.id = m.tag_id
WHERE t.deleted_at IS NULL
	AND t.purged_at IS NULL
	AND t.status IN ('due', 'waiting')
	AND g.name IN (:tag1, :tag2)
GROUP BY t.id
HAVING COUNT(DISTINCT g.name) = :tags_len
ORDER BY t.updated_at DESC;
```

補足:

- title/note 検索と組み合わせる場合は WHERE に `(t.title LIKE :q OR t.note LIKE :q)` を追加する。

### 22.5 タグ付与（上限5の確認付き）

```sql
-- 1) 現在のタグ数
SELECT COUNT(*) AS cnt
FROM task_tag_map
WHERE task_id = :task_id;

-- 2) タグが無ければ作る（nameは正規化済みを渡す）
INSERT INTO task_tags(id, name, created_at)
VALUES(:tag_id, :name, :now)
ON CONFLICT(name) DO NOTHING;

-- 3) tag_id を取得
SELECT id FROM task_tags WHERE name = :name;

-- 4) 関連付け
INSERT OR IGNORE INTO task_tag_map(task_id, tag_id)
VALUES(:task_id, :tag_id);
```

### 22.6 アーカイブ（復元可能な論理削除）

```sql
UPDATE tasks
SET deleted_at = :now,
		status = 'archived',
		updated_at = :now
WHERE id = :task_id
	AND deleted_at IS NULL
	AND (purged_at IS NULL);
```

### 22.7 復元

```sql
UPDATE tasks
SET deleted_at = NULL,
		status = CASE
			WHEN next_review_at IS NOT NULL AND next_review_at <= :now THEN 'due'
			ELSE 'waiting'
		END,
		updated_at = :now
WHERE id = :task_id
	AND deleted_at IS NOT NULL
	AND (purged_at IS NULL);
```

### 22.8 アーカイブ済みの「完全な論理削除（復元不可）」

```sql
UPDATE tasks
SET purged_at = :now,
		updated_at = :now
WHERE id = :task_id
	AND deleted_at IS NOT NULL
	AND purged_at IS NULL;
```

## 16. パフォーマンス/インデックス要件

- Due/Waitingの一覧取得が主クエリとなるため、`tasks(status, next_review_at)` の複合INDEXを必須とする。
- 履歴取得は `completion_events(task_id, completed_at)` のINDEXを必須とする。
- 1タスクの履歴が大きくなっても、`find_next_review` は二分探索40回で一定回数の計算になること。


