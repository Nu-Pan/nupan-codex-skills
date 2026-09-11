---
name: validate-openai-structured-output-schema
description: OpenAI Structured Outputs や Codex CLI の --output-schema に渡す JSON Schema の作成・変更・レビューで使用する。配布 CLI でバージョン付きプロファイルへの適合性をオフライン検証する。
---

# Structured Outputs schema をオフライン検証する

利用者が指定した schema file を優先する。
指定がなければ、呼び出し元や設定から OpenAI Structured Outputs 用のファイルを特定する。
この validator は、バージョン付きプロファイルへの適合性を判定する。

## 配布 CLI で検証する

この `SKILL.md` があるディレクトリを `<skill-root>` として実行する。

```bash
python3 <skill-root>/scripts/validate_schema.py \
  --profile openai-structured-outputs-2026-08 \
  path/to/schema.json
```

機械処理する場合は `--format json` を追加する。
終了コードから検証状態を判断する。

| 終了コード | 結果 |
| --- | --- |
| `0` | プロファイルに適合した。 |
| `1` | 入力や schema の違反を検出した。全診断を確認する。 |
| `2` | 引数、読み込み、内部処理などの問題で検証できなかった。 |

## 診断を解消する

修正の依頼では、診断箇所と関連する定義を一緒に読み、意図する契約を保って不整合を解消する。
レビューだけの依頼ではファイルを変更しない。
修正後は同じプロファイルで再検証する。

診断はプロファイルへの適合性の根拠として使い、アプリの正本仕様を validator の実装から逆算しない。
未知の keyword もエラーとして扱い、一般の JSON Schema validator の成功で代用しない。
同じ schema の検証を複数の規則が求める場合は、結果を共用する。

## 結果を報告する

使用したプロファイル、対象ファイル、終了結果を示す。
違反が残る場合は診断コードと JSON Pointer を示し、検証不能を成功としない。

この手順では API や Codex CLI を呼び出さない。
オフライン検証の成功を、リモートサービスの受理の保証として扱わない。
