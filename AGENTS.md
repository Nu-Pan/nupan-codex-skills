# リポジトリの運用規則

## 正本

全スキルに共通する構造と保守方法は、[`docs/skill-repository-spec.md`](docs/skill-repository-spec.md) を正本とする。
新規スキルの追加では、[`docs/adding-a-skill.md`](docs/adding-a-skill.md) の手順にも従う。
開発環境の構築と pytest の実行では、[`docs/development-environment.md`](docs/development-environment.md) の規約に従う。

各スキルの実行時仕様は、`skills/{{skill-name}}/SPEC.md` を正本とする。
スキル固有の保守規則がある場合は、そのスキルの `AGENTS.md` も適用する。

## 変更

スキルを追加または変更するときは、共通仕様に定めた順序で作業する。
実行時仕様を変更するときは、先に対応する `SPEC.md` を変更する。

日本語文書は GFM で構造化する。
一文一義とし、要点と列挙の位置づけを詳細や個別項目より先に示す。

## 完了ゲート

変更したスキルを指定して、リポジトリ検査を実行する。
対象スキルに `tests/` がある場合は、そのテストも実行する。

```bash
python3 -m pytest skills/{{skill-name}}/tests
python3 scripts/validate_skills.py {{skill-name}} [{{skill-name}} ...]
```

リポジトリ全体へ影響する変更では、全スキルとリポジトリツールを検証する。

```bash
python3 scripts/validate_skills.py
python3 -m pytest tests skills
```

スキルの追加、削除、適用条件、実行時規則、合成規則を変更した場合は、`skill-composition.json` で影響する単独シナリオと組み合わせシナリオも前向き評価する。
