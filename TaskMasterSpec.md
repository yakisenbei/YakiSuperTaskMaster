
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
	 - ただし、初期設定で「追加直後は待ちに入れる」を選べる実装も許容する。

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

### 4.5 通知（任意/拡張）

- Dueになったタスク数が一定以上になった場合に通知する。
- 1件でもDueになったら通知する設定を持てる。

### 4.6 設定（目標日数・テーマ）

- ユーザーは「記憶時間の目標日数（= horizon days / $T_{target}$ のオフセット）」を変更できる。
	- 初期値は **365日（1年）** とする。
	- 変更は **今後の完了から適用**する（既存 waiting の next_review_at は即時には変更しない）。
	- 設定画面に **「全タスク再計算」ボタン**を用意し、任意で一括再計算できる。
- ユーザーは表示テーマを切り替えできる。
	- ライトモード / ダークモード
	- 可能なら「システム設定に追従」も用意する（任意）。

### 4.7 復習の早期終了（ユーザー判断による除外）

- 復習待ちキュー（Due）および復習インターバル中（Waiting）のタスクについて、
	ユーザーが「十分に復習できた」と判断した場合、それ以降の復習サイクルから除外できる。
- 本仕様では、データは**論理削除**とし、アーカイブは復元可能とする。
	- アーカイブ済みはDue化（復習サイクル）対象から外してよい。
	- 終了理由の記録は行わない。

用語の整理:

- **アーカイブ**: 論理削除（復元可能）
- **削除**: UI文言として「削除」を出す場合でも、内部は論理削除で統一してよい

## 5. データ要件（概念モデル）

### 5.1 Task

- id: UUID
- title: string
- note: string（任意）
- status: enum { due, waiting, archived }
- created_at: datetime
- updated_at: datetime
- next_review_at: datetime（Due/Waiting判定の基準）
- history_times: datetime[]（完了イベントの時刻列）
- review_count: int（= len(history_times)、冗長保持は任意）
- params_override: object（任意。タスク単位でチューニングパラメータを上書き可能）

### 5.2 CompletionEvent（任意: 正規化する場合）

- id: UUID
- task_id: UUID
- completed_at: datetime

※ 実装では `history_times` 配列に保持してもよいし、RDBでイベントとして保持してもよい。

## 6. 復習インターバル計算ロジック

本仕様は、ユーザー提示の計算式（ACT-R風 base activation と想起確率）に従う。

### 6.1 パラメータ（チューニング可能定数）

- $d$: decay（忘却の減衰係数）
	- 既定値: 0.5
- $s$: noise（シグモイドのなだらかさ）
	- 既定値: 0.4
- $\tau$: retrieval threshold（想起の閾値）
	- 既定値: 0.0
- $p_{target}$: 将来時点で保証したい想起確率
	- 既定値: 0.90
- $T_{target}$: 想起確率を保証したい将来の評価時点
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
- `candidate_time` は必ず $now + 1$ minute 以上になるよう下限を適用してよい（推奨）。

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
	- UI表示/通知の都合で、返却した next_review_at は「分」または「5分刻み」などに丸めてもよい。
	- ただし、Due判定の正当性を崩さないよう一方向（未来側）への丸めを推奨する。

## 7. 状態遷移

### 7.1 状態

- due: ユーザーに提示すべき
- waiting: 将来時刻まで待機
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
- 完了ボタン
- 履歴一覧（timestampの列）

### 8.3 タスク作成/編集

- title（必須）
- note（任意）

## 9. 非機能要件

- 時刻はタイムゾーンを保持する（推奨: UTC保存 + 表示はローカル変換）。
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
- 推奨UI構成: Qt Widgets（`QMainWindow` + `QTableView/QListView` + `QDialog`）。

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
- 初期実装は配布性を優先し **SQLite** を推奨する。
	- 将来的にPostgreSQL等へ差し替えられるよう、SQL方言依存を最小化する。
- Python DBアクセスは以下のいずれか（実装方針としてどちらでも可）
	- (A) `sqlite3`（標準） + 手書きSQL（推奨: シンプルかつ依存が増えない）
	- (B) SQLAlchemy（拡張時に有利）

本仕様書のDDL例はSQLite互換を基本とする。

## 12. アーキテクチャ（推奨）

### 12.1 レイヤ構成

- **UI層（PySide6）**
	- 画面/ダイアログ、入力検証、ユーザー操作の受け口
- **アプリケーション層（UseCase/Service）**
	- 完了操作、次回復習計算、状態遷移、Due更新などの業務ロジック
- **ドメイン層（Model）**
	- Task、ReviewParams 等のデータ構造（純粋Python）
- **インフラ層（Repository/DAO）**
	- SQL発行、トランザクション、マイグレーション

### 12.2 時刻の取り扱い（実装規約）

- DB保存は **UTC** を基本とする。
- Python内部は `datetime`（timezone-aware）を基本とする。
- DBのDATETIMEは実装上、次のどちらかに統一する（混在禁止）:
	- (推奨) **INTEGER（Unix epoch seconds）**
	- もしくは TEXT（ISO 8601: `YYYY-MM-DDTHH:MM:SSZ`）

本仕様では、検索・比較・インデックス効率の観点から **epoch seconds を推奨**する。

## 13. DB設計（SQLスキーマ）

### 13.1 方針

- `history_times` を配列で持つのではなく、**CompletionEventとして正規化**して保持する。
	- 理由: SQLでの集計・参照・監査が容易、データ破損しにくい。
- Taskは `next_review_at` をキャッシュとして保持する（Due判定高速化）。

### 13.2 テーブル一覧

- `tasks`: タスク本体
- `completion_events`: 完了（復習）イベント（時系列ログ）
- `task_params`: タスク単位のパラメータ上書き（任意・拡張）

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

-- タスク単位のパラメータ上書き（必要になったら有効化）
CREATE TABLE IF NOT EXISTS task_params (
	task_id    TEXT PRIMARY KEY,
	d          REAL,
	s          REAL,
	tau        REAL,
	p_target   REAL,
	horizon_days INTEGER,                           -- 例: 365

	FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE
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

#### 13.4.1 論理型 → SQLite推奨型

- **UUID**
	- 論理型: UUID
	- SQLite: `TEXT`（例: `"550e8400-e29b-41d4-a716-446655440000"`）
	- 他RDB: PostgreSQLなら `UUID`

- **文字列**
	- 論理型: string
	- SQLite: `TEXT`

- **真偽**
	- 論理型: boolean
	- SQLite: `INTEGER`（0/1）
	- 他RDB: `BOOLEAN`

- **整数**
	- 論理型: int
	- SQLite: `INTEGER`

- **浮動小数**
	- 論理型: float
	- SQLite: `REAL`

- **日時（UTC）**
	- 論理型: datetime
	- SQLite推奨: `INTEGER`（epoch seconds）
	- 代替: `TEXT`（ISO 8601）
	- 他RDB: `TIMESTAMP WITH TIME ZONE`（または `TIMESTAMPTZ`）

- **列挙**
	- 論理型: enum
	- SQLite: `TEXT` + `CHECK(...)`

#### 13.4.2 Python（PySide6）での型変換ルール

- DB保存/比較のため、`datetime` は epoch seconds（int）へ変換して保存する。
- UI表示はローカルタイムへ変換して表示してよい。
- 精度は秒単位を基本とし、UI都合の丸め（分/5分）は保存前に行ってよい（6.5参照）。

## 14. 主要ユースケース（CRUD + 完了）

### 14.1 タスク作成

入力:

- title（必須）
- note（任意）

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

推奨実装:

- アプリ起動時に1回
- 一覧表示の更新タイミングで適宜
- さらに `QTimer` で1分ごと等に実行（軽量）

### 14.4 タスクのアーカイブ（論理削除）

目的:

- 「十分に復習できた」判断で、復習サイクル対象から外す（復元可能）。

処理:

- `tasks.deleted_at = now` をセット
- `tasks.status = 'archived'` としてよい（UIの見た目用）

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

## 15.5 検索（title/note 同時検索）

- 検索対象は title と note の両方とする。
- SQLiteでは `LIKE` による部分一致を最小実装とする。
	- 将来的に `FTS5` を採用して高速化してもよい（任意）。

最小クエリ例:

```sql
SELECT *
FROM tasks
WHERE deleted_at IS NULL
	AND status IN ('due', 'waiting')
	AND (title LIKE :q OR note LIKE :q);
```

## 15.6 キュー（2種類）とソート

一覧は以下の2キューを持つ:

- **復習待ちキュー（Due）**: `status='due'` かつ `deleted_at IS NULL`
	- ソート: **古い順**（主に `next_review_at` 昇順、NULLは末尾）
- **インターバル待ちキュー（Waiting）**: `status='waiting'` かつ `deleted_at IS NULL`
	- ソート: **新しい順**（主に `next_review_at` 降順、NULLは末尾）

※ UIでソートの切替（昇順/降順）を追加してもよいが、デフォルトは上記。

## 15. 画面要件（PySide6前提の詳細）

### 15.1 メインウィンドウ

- タブまたはセグメントで状態を切替

- タブまたはセグメントで状態を切替
	- Due
	- Waiting
	- Archived
- 一覧は `QTableView` 推奨
	- Due: タイトル、最終完了時刻、復習回数、（任意）推定想起確率
	- Waiting: タイトル、次回復習時刻（ローカル表示）、残り時間

UI方針:

- **ボタン数は最小化**する（主要操作は各行のコンテキストメニュー/右クリック/三点メニューに集約）。
- 主要導線は「完了」「追加」「検索/フィルタ」のみに寄せる。
- 角が立たない **柔らかな形状**（角丸、余白広め、控えめな枠線）を採用する。

### 15.1.1 テーマ切り替え（ライト/ダーク）

- メニューまたは設定画面からライト/ダークを切り替えできる。
- PySide6では以下の方針のいずれかで実現する。
	- (A) Qt StyleSheet（QSS）でライト/ダーク2種を用意して切替
	- (B) `QPalette` を切替
- テーマ切替は即時反映（アプリ再起動不要）を目標とする。

### 15.2 タスク作成/編集ダイアログ

- `QDialog`
- title必須のバリデーション

### 15.3 タスク詳細

- 完了ボタン（Due/Waiting両方で押せるかは実装選択、基本はDueで押す）
- 履歴一覧（`completion_events` の completed_at）
- （任意）パラメータ上書きUI（`task_params`）

追加操作:

- 「十分に復習できた」
	- 既定動作: アーカイブ
	- 代替: 完全削除（確認ダイアログ必須）

## 17. 設定の永続化（ユーザー設定）

### 17.1 設定項目

- horizon_days（記憶時間の目標日数）
	- 型: int
	- 初期値: 365
	- 制約: 1〜365
- theme
	- 型: enum { system, light, dark }（systemは任意）
	- 初期値: system（systemが無い場合はlight）

### 17.2 保存先

- 簡易: `QSettings` を使用してOS標準の設定ストアへ保存
- 代替: DBに `app_settings` テーブルを作成して保存（将来の同期/移行に有利）

### 17.3 （DB保存する場合のDDL例）

```sql
CREATE TABLE IF NOT EXISTS app_settings (
	key   TEXT PRIMARY KEY,
	value TEXT NOT NULL
);

```

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
- 設定画面から任意タイミングでバックアップを作成できる。
- 本仕様では、バックアップは **単純コピー** でよい。
	- 推奨: コピー前にトランザクション中の処理がない状態にする（UIを一時的にロックする等）。

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

- **「完了」ボタン = `good`（ワンクリック）** とする。
- 「▼」で評価選択（`again/hard/good/easy`）を表示し、選択されたgradeで完了処理を実行する。
- PySide6実装例: `QToolButton` の MenuButtonPopup を使用して「主ボタン + ▼」を構成する。

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

### 22.3 title/note検索

```sql
SELECT t.*
FROM tasks t
WHERE t.deleted_at IS NULL
	AND t.purged_at IS NULL
	AND t.status IN ('due', 'waiting')
	AND (t.title LIKE :q OR t.note LIKE :q)
ORDER BY t.updated_at DESC;
```

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


