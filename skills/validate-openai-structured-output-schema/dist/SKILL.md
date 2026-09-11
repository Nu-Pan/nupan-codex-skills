---
name: validate-openai-structured-output-schema
description: OpenAI Structured Outputs や Codex CLI の --output-schema に渡す JSON Schema の作成・変更・レビューで使用する。配布 CLI でバージョン付きプロファイルへの適合性をオフライン検証する。
---

# Structured Outputs schema をオフライン検証する

利用者が指定した schema file を優先し、指定がなければ呼び出し元や設定から OpenAI Structured Outputs 用のファイルを特定する。配布 CLI はバージョン付きプロファイルの許可リストと上限を検査する。

## 配布 CLI を実行する

この `SKILL.md` があるディレクトリを `<skill-root>` として実行する。

```bash
python3 <skill-root>/scripts/validate_schema.py \
  --profile openai-structured-outputs-2026-08 \
  path/to/schema.json
```

機械処理する場合は `--format json` を追加し、終了コードから検証状態を判断する。

| 終了コード | 結果 |
| --- | --- |
| `0` | プロファイルに適合した。 |
| `1` | 入力や schema の違反を検出した。全診断を確認する。 |
| `2` | 引数、読み込み、内部処理などの問題で検証できなかった。 |

未知の keyword もエラーになる。一般の JSON Schema validator の成功では、この固有のプロファイルの検証を代用しない。

## 診断を解消して報告する

修正の依頼では、診断箇所と関連する定義を一緒に読み、意図する契約を保って不整合を解消する。契約の根拠はアプリの正本に、プロファイル適合性の根拠は診断結果に求める。レビューだけの依頼ではファイルを変更しない。

修正後は同じプロファイルで再検証し、同じ schema の検査は併用する規則と共用する。結果には使用したプロファイル、対象ファイル、終了結果を示す。違反が残る場合は診断コードと JSON Pointer を示し、検証不能を成功としない。

API や Codex CLI を呼び出さずに検証する。この成功はプロファイルへの適合を意味し、リモートサービスの受理を保証しない。
