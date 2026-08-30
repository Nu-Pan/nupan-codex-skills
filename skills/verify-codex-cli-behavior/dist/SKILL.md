---
name: verify-codex-cli-behavior
description: Codex CLI をローカル process として直接または SDK、library、wrapper 経由で使用するアプリを設計、実装、変更、レビューするときに使用する。対象版の openai/codex production source で重要挙動を確認し、固定 SHA permalink、実測、互換性対策を成果物へ残す。Codex CLI を開発道具として使うだけの作業や、CLI を起動しない OpenAI API 統合には使用しない。
---

# Codex CLI 挙動をソースで検証する

## 対象と revision を確定する

- 対象アプリの仕様、設定、lock file、integration code、テストから、アプリが依存する重要な Codex CLI 挙動を列挙する。
- 引数、設定優先順位、標準入出力、JSONL event、終了コード、認証、approval、sandbox、signal、process lifecycle のうち、設計、制御、互換性、またはテストが依存する挙動だけを対象にする。
- アプリが宣言する commit または exact version を最初に採用する。
- 宣言から特定できなければ、アプリが実際に起動する CLI の commit または version を確認する。
- version だけが判明した場合は、`openai/codex` の `rust-v<version>` release tag が指す commit を解決する。
- annotated release tag は `^{commit}` または remote の peeled `^{}` reference で commit まで dereference し、tag object の SHA を permalink に使わない。
- lightweight tag でも、tag が指す object が commit であることを確認する。
- revision を特定できなければ、GitHub Releases の最新 stable release が指す commit を代用する。
- prerelease は、利用者または対象アプリが明示している場合だけ採用する。
- 代用理由を記録し、代用 revision と対象環境が一致すると断定しない。

## Production source を確認する

- 対象アプリの正本仕様と利用者の要求を、Codex CLI の source を理由に上書きしない。
- 各重要挙動を、対象 revision の `openai/codex` production implementation で確認する。
- 判断に必要な呼び出し元と実装先をたどる。
- permalink を記録する前に、SHA が commit object であり、示す path と行範囲がその commit に存在することを確認する。
- 各挙動に、次の形式で必要最小限の行範囲を示す permalink を一つ以上付ける。

```text
https://github.com/openai/codex/blob/<full-40-character-commit-sha>/<path>#L<start>-L<end>
```

- `main` などの可変 branch、tag 名、repository root、issue、pull request、文書、release notes、test code だけを根拠にしない。
- test code、公式文書、release notes は、production implementation の補強にだけ使う。
- source と文書または実測が異なる場合は、revision と実行条件を再確認する。
- 不一致が残る場合は production source を実装判断で優先し、不一致と不確実性を記録する。
- source の内部構造から将来互換性または公開契約を断定しない。
- 公開されていない server-side semantics は、CLI 側の request、response、error handling の境界までを根拠化し、確認不能範囲を明記する。
- GitHub 上の production implementation を確認できない重要挙動を、確認済みまたは完了として扱わない。

## 根拠を成果物へ残す

変更が許可されている場合は、同じ immutable permalink を次の場所へ残す。

1. 対象リポジトリの規約に従い、既存の正本仕様または設計文書へ挙動、version、platform、設定条件、根拠を記録する。
2. 適切な既存文書がなければ、`docs/codex-cli-behavior-evidence.md` を作成する。
3. 挙動へ依存する integration code の直前または直近に、permalink を含むコメントを置く。

- 文書へ focused verification の結果または未実施理由も記録する。
- 対象 revision の source に根拠付ける重要挙動を version-sensitive として扱う。
- 各重要挙動への依存には、version pin、起動時の version check、または安全側の capability fallback を設ける。
- capability fallback を選ぶ場合は、失敗条件と利用者への通知を明確にする。
- レビューだけを依頼された場合はファイルを変更せず、欠けている文書、近接コメント、permalink、互換性対策、実測を所見として報告する。

## Focused verification を行う

- 安全かつ実行可能なら、source と同じ CLI version、platform、設定で各重要挙動を絞って観測する。
- 一つの確認で複数の条件を変えない。
- version 表示、help、引数検査など、外部作用を必要としない確認を優先する。
- 一時 workspace と非機密の入力を使う。
- 認証、network access、課金、外部変更、広い filesystem access が必要な確認では、既存の権限と対象リポジトリの規則を守る。
- command または手順、条件、終了結果、観測内容を記録する。
- 実施できなければ、理由と判断への影響を記録する。
- source 確認を実測済みとして扱わない。
- 実測を別の version、platform、設定の互換性保証として扱わない。

## 結果を報告する

- 重要挙動ごとに、対象 version、platform、full commit SHA、挙動、production source permalink、実測結果を要約する。
- production implementation の permalink URL 自体を最終報告へ記載し、設計文書やコードへのリンクだけで代用しない。
- 代用 revision、不一致、未実施の実測、確認不能範囲を明記する。
- 更新した設計文書、近接コメント、version pin、version check、または fallback を示す。
- 各重要挙動に production source permalink がない場合は、完了できない理由を明示する。
- 最終応答の送信直前に、source 確認済みの各重要挙動について `https://github.com/openai/codex/blob/<full-40-character-commit-sha>/<path>#L<start>-L<end>` 形式の検証済み URL が応答本文に一つ以上あることを確認し、漏れている場合だけ追加する。
- source 未確認の挙動には URL を作らず、未確認の理由を報告する。
