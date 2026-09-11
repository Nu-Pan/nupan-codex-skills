---
name: verify-codex-cli-behavior
description: Codex CLI をローカル process として使うアプリの設計・実装・レビューで使用する。対象版の production source と安全な実測で重要挙動を確かめ、根拠と互換性対策を追跡可能にする。CLI を開発道具として使うだけの場合は使用しない。
---

# Codex CLI への依存をソースと実測で確かめる

アプリの要求と integration code から、誤認すると設計や制御、互換性の判断が変わる挙動を特定する。
対象アプリが依存しない挙動を網羅するためだけに調査しない。

## 対象版を確定する

アプリが宣言する commit または exact version を優先する。
特定できなければ、実際に起動する CLI の版や lock file を確認する。
version から `openai/codex` の `rust-v<version>` release tag が指す commit を解決する。
tag は commit object まで解決し、annotated tag の tag object SHA を使わない。
`^{commit}` または remote の peeled reference を利用できる。

対象を特定できなければ最新 stable release を調査用に代用し、理由と対象環境の未確認を示す。
prerelease は利用者やアプリが指定した場合に使う。

## 根拠を確認する

重要な挙動を、対象 revision の production implementation で確認する。
必要な呼び出し元と実装先をたどり、実在する commit・path・行範囲を確かめる。
根拠には、判断を支える行範囲の immutable permalink を使う。

```text
https://github.com/openai/codex/blob/<full-40-character-commit-sha>/<path>#L<start>-L<end>
```

公式文書やテストは解釈の補強に使い、production source の確認を置き換えない。
CLI の実装を理由にアプリの正本仕様や利用者の要求を書き換えない。
現在の内部実装から将来の互換性や公開契約を保証しない。

ソースと文書や実測が異なる場合は、revision と実行条件を調べる。
不一致が残れば、確認した事実を分けて示して実際の挙動を断定しない。
公開されていない server-side の意味は、CLI 側で確認できる境界までを根拠化する。

## 実測と互換性を確かめる

安全に実行できる場合は、同じ version・platform・設定で重要な挙動を絞って観測する。
条件差を追える確認を選び、一時 workspace と非機密の入力を使う。
認証や外部作用が必要な操作は、既存の権限とリポジトリの規則に従う。
実測できなければ理由と判断への影響を示し、ソース確認を実測済みとしない。

ソースに根拠付けた重要な依存には、対応版の pin、起動時の version check、または安全側の capability fallback を設ける。
fallback の失敗条件と利用者への通知を明らかにする。
複数の依存を守る対策は共用できる。

## 根拠を残して報告する

変更の依頼では、既存の設計文書など一箇所に根拠の詳細を集約する。
適切な文書がなければ `docs/codex-cli-behavior-evidence.md` を作る。
挙動と依存理由、revision、実行条件、production permalink、実測結果、不確実性を追跡できるようにする。
integration code の必要な箇所から根拠への参照を置き、同じ詳細を複製しない。

レビューだけの依頼ではファイルを変更しない。
重要な依存の根拠や互換性対策を追えない場合は影響を報告し、文書名やコメントの欠落だけで挙動上の不整合と断定しない。

最終報告では、確認した挙動、判断に必要な条件、検証結果、根拠への参照を簡潔に示す。
詳細を記録した文書があれば参照し、参照先がなければ報告自体に production permalink と必要な根拠を載せる。
未確認の重要挙動は理由と影響を明記し、production source を確認できないものが残れば検証完了としない。
