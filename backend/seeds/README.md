# コンピュータサイエンス学部の科目データ

全学部・大学院の追加シード、出典、再生成・投入手順と未確認課程は[2026年度対応表](../../docs/curriculum_coverage_2026.md)を参照。本書のCSシードは既存IDを保持して先に投入する。


確認元は東京工科大学2026年度学生便覧（八王子キャンパス）
`2026hcgakuseibinran.pdf`。2026年10月11日に、冊子83〜84ページの専攻・コースと、
冊子85〜92ページ（PDF87〜94ページ）の教育課程表を抽出し、表の画像と照合した。
原本はリポジトリに含めない。原本のSHA-256と表のセル値を
`cs_2026.source.json` に保存している。

## ファイルと再生成

- `cs_2026.json`：CLIで投入するシード。
- `cs_2026.source.json`：PDF表の転記。結合セルはnull、元の科目名・種別・単位・開講列・授業形態を保持。
- `build_cs_seed.py`：転記からシードを生成する標準ライブラリだけのスクリプト。

`backend/` から実行する。

```sh
uv run python seeds/build_cs_seed.py
uv run --locked python -m scripts.seed_subjects --file seeds/cs_2026.json
```

| 登録内容 | 件数 |
| --- | ---: |
| 課程・開講元 | 6 |
| 選択対象カリキュラム | 4 |
| 分類 | 68 |
| 科目 | 131 |
| 開講期 | 161 |
| 課程別科目 | 498 |

先進情報専攻3コースは各126科目、社会情報専攻は120科目。
先進情報専攻では専門教育科目表の「コース毎の種別」欄を使用し、空欄は選択とする。
例えば「人工知能」は人工知能コースのみ選択必修。「WebプログラミングⅠ」は先進情報専攻では必修、
社会情報専攻では選択必修。科目本体を共有しても、本人課程での種別は共有しない。

## コード・分類・開講期

`CS-ADV-INFRA` / `CS-ADV-HUMAN` / `CS-ADV-AI` / `CS-SOCIAL` が4課程。
`CS` と `CS-ADV` は共通科目の開講元を表す中間階層で、選択用カリキュラムを持たない。
学科欄は便覧に独立した学科階層がないためnull。学部・専攻・コースの名称は便覧表記を使用。

`CS-C001` 等はアプリ内部の科目コードであり、大学の正式科目コードではない。
UUIDは内部コードから決定的に生成する。コード割当は既存科目について変更しない。
この転記では両専攻の共通科目を科目名・単位・授業形態・開講欄の照合によって共有している。
他学部の同名科目を同一と推測して統合する処理ではない。

各課程に実学基礎・専門基礎教育・専門教育の3区分と、便覧表の14科目群を登録。
`level=0` が区分、`level=1` が科目群。子分類は親と同じカリキュラムに属する。
「健康と科学」は教育課程表のセルに従いウェルビーイングに分類した。

`term_code=first/second` は前期／後期、`semester_order=1..8` は1年次前期から4年次後期までの
表の列位置を表す。複数列に記載された科目は全列を保持する。
`academic_year` は暦年であり、便覧の学年列から暦年を推測しないためnull。
○は担当教員の指示、＊は学年共通開講（生成AI活用入門はクォーター開講）、
※は専門演習Ⅰの1年次履修条件として `source_note` に残す。
注記はこの段階では履修可否や卒業判定を実行する規則ではない。

授業形態の原文は `teaching_type_label` に保存する。「講義・演習」と「実技」は
既定の5区分に単一対応しないため `teaching_type=other` とし、原文を失わせない。

## 適用範囲と未実装部分

カリキュラムコードの `HANDBOOK-2026` は参照便覧の年度であり、2026年度入学者のみへ適用する
という意味ではない。適用入学年度の開始・終了は根拠未確認のためnull、
`verification_status=unverified`。転記完了を課程の判定対応完了として扱わない。
開始年度を確認したカリキュラムのみ `verified` を設定できる。終了年度nullは上限未指定。
現在の卒業判定は2026年度便覧を基準として使用し、適用年度が未確認のままでも計算する。
この運用方針によって確認状態・適用年度を書き換えることはない。

今回の対象は教育課程表の科目データ。冊子94の卒業要件の条件モデル・換算・他学部算入規則、
他学部マスタ、認証、成績、推薦、判定APIは含まない。
冊子94の必修小計はテストで照合し、先進情報の16/21/21、社会情報の16/18/21と一致することを確認する。
未確認の適用範囲や換算規則を正式な値として補完しない。

2026年10月16日に、卒業要件・算入規則のモデルと別シードを追加した。
科目シードの6配列契約は維持する。対象・確認状態・投入手順は
[卒業要件マスタ](requirements.md)を参照。判定処理・判定APIは引き続き未実装。

## シード契約

トップレベルは `academic_programs`, `curricula`, `classifications`, `courses`,
`course_offerings`, `curriculum_courses` の6配列。空配列も明示する。
UUID・必須文字列・正整数／非負整数を検証し、未知フィールド・小数・真偽値・文字列数値を拒否する。
検証状態は `unverified/verified`、科目種別は `required/selective/elective`。
既存DBの参照先を使う追加シードも許可する。

再投入は同一内容をスキップし、内容の異なる既存ID・重複コードはエラー。
既存マスタは削除・更新せず、全データ消去機能も設けない。

## 実装ファイル

- `modules/subjects/grad_checker_subjects/application/dto/subject_data.py`・`modules/subjects/grad_checker_subjects/application/services/subject_data_validation.py`：投入する課程・科目データの型と整合性検証。
- `modules/subjects/grad_checker_subjects/application/use_cases/import_subject_data.py`：既存データとの照合・全体の検証と、一つの書込みトランザクション（Unit of Work）での追加投入。
- `modules/subjects/grad_checker_subjects/infrastructure/subject_data_import.py`：JSONの読み込みと、投入済みデータの読取り・追加。
- `modules/subjects/grad_checker_subjects/infrastructure/subject_models.py`：課程・科目データを保存する6テーブル。
- `modules/subjects/grad_checker_subjects/application/errors/subject_data.py`：投入処理の例外。
- `api/presentation/subject_list.go`：科目一覧を取得するAPI。
