---
name: validate-openai-structured-output-schema
description: Codex CLI の --output-schema または OpenAI Structured Outputs に渡す JSON Schema を作成、変更、レビュー、検証するときに使用する。バージョン付きの fail-closed プロファイルで、JSON 文法、対応サブセット、object 規則、参照、サイズ上限を API 呼び出しなしで機械検証する。一般用途の JSON Schema だけを扱う作業や、生成済み JSON instance の検証には使用しない。
---

# OpenAI Structured Outputs schema を検証する

## 対象を特定する

- 利用者が指定した schema file を優先する。
- 指定がない場合は、変更差分、`codex exec --output-schema` の呼び出し、設定、テストから OpenAI Structured Outputs 用の file を特定する。
- 一般用途の JSON Schema を、用途の根拠なしにこのプロファイルで検証しない。

## validator を実行する

この skill の `SKILL.md` がある directory を `<skill-root>` として、対象ごとに次を実行する。

```bash
python3 <skill-root>/scripts/validate_schema.py \
  --profile openai-structured-outputs-2026-08 \
  path/to/schema.json
```

機械処理できる診断が必要な場合は、`--format json` を追加する。

- 終了コード `0` の場合だけ、その file を profile 適合とする。
- 終了コード `1` の場合は、最初の一件だけでなく全診断を確認する。
- 終了コード `2` の場合は、検証済みとせずに読み込み、引数、または内部処理の問題を報告する。

## 診断へ対応する

- 変更を依頼されている場合は、診断が示す JSON Pointer の schema node を最小限に修正する。
- レビューだけを依頼されている場合は、file を変更せずに診断を報告する。
- 修正後は、同じ profile で validator を再実行する。
- 未知 keyword を警告として無視しない。
- 一般の JSON Schema validator の成功を、この validator の代わりにしない。

## 結果を報告する

最終報告には、使用した profile、検証した file、終了結果を含める。
失敗が残る場合は、診断 code と schema pointer を示す。

この skill の標準手順では、OpenAI API または Codex CLI を呼び出さない。
オフライン検証の成功を、remote service が必ず受理する保証として報告しない。
