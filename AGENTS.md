# リポジトリの運用規則

## 正本

全スキルに共通する構造と保守方法は、[`docs/skill-repository-spec.md`](docs/skill-repository-spec.md) を正本とする。
新規スキルの追加では、[`docs/adding-a-skill.md`](docs/adding-a-skill.md) の手順にも従う。

各スキルの実行時仕様は、`skills/{{skill-name}}/SPEC.md` を正本とする。
スキル固有の保守規則がある場合は、そのスキルの `AGENTS.md` も適用する。

## 変更

スキルを追加または変更するときは、共通仕様に定めた順序で作業する。
実行時仕様を変更するときは、先に対応する `SPEC.md` を変更する。

日本語文書を作成または変更するときは、`skills/japanese-writing-skill/SPEC.md` の文章規則を適用する。

## 完了ゲート

変更したスキルを指定して、リポジトリ検査を実行する。

```bash
python3 scripts/validate_skills.py {{skill-name}} [{{skill-name}} ...]
```

共通仕様、雛形生成、または検査処理を変更した場合は、全スキルとリポジトリツールを検証する。

```bash
python3 scripts/validate_skills.py
python3 -m unittest discover -s tests -v
```
