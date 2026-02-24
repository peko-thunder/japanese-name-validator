"""namedicデータ変換スクリプト

workspace/namedic/data/*.json の64ファイルを読み込み、
漢字1文字目のUnicodeコードポイントでグループ化して
data/surnames/{XXXX}.json として出力する。

使用方法:
    python scripts/convert_namedic.py
"""

import json
import sys
from pathlib import Path

# プロジェクトルートを基準にパスを設定
PROJECT_ROOT = Path(__file__).parent.parent
NAMEDIC_DIR = PROJECT_ROOT / "workspace" / "namedic" / "data"
OUTPUT_DIR = PROJECT_ROOT / "data" / "surnames"


def load_namedic_files() -> dict[str, list[str]]:
    """全namedicファイルを読み込み、漢字→読みリストのマップを返す

    同一漢字が複数ファイルに存在する場合は読みリストをマージ（重複除去）。

    Returns:
        {漢字: [読み1, 読み2, ...]} の辞書
    """
    merged: dict[str, list[str]] = {}
    total_entries = 0

    namedic_files = sorted(NAMEDIC_DIR.glob("*.json"))
    if not namedic_files:
        print(f"エラー: {NAMEDIC_DIR} にJSONファイルが見つかりません", file=sys.stderr)
        sys.exit(1)

    print(f"{len(namedic_files)} ファイルを読み込み中...")

    for file_path in namedic_files:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        entries = data.get("entries", [])
        total_entries += len(entries)

        for entry in entries:
            kanji = entry.get("kanji", "")
            readings = entry.get("readings", [])

            if not kanji or not readings:
                continue

            if kanji in merged:
                # 既存の読みリストにマージ（重複除去）
                existing = set(merged[kanji])
                for r in readings:
                    if r not in existing:
                        merged[kanji].append(r)
                        existing.add(r)
            else:
                merged[kanji] = list(readings)

    print(f"  読み込み完了: {len(namedic_files)} ファイル、{total_entries} エントリー（ソース合計）")
    print(f"  重複除去後: {len(merged)} ユニーク漢字")
    return merged


def group_by_first_char(data: dict[str, list[str]]) -> dict[str, dict[str, list[str]]]:
    """漢字1文字目のUnicodeコードポイントでグループ化

    Args:
        data: {漢字: [読み]} の辞書

    Returns:
        {16進コードポイント: {漢字: [読み]}} の辞書
        例: {"5C71": {"山田": ["やまだ"], "山本": ["やまもと"]}}
    """
    groups: dict[str, dict[str, list[str]]] = {}

    for kanji, readings in data.items():
        if not kanji:
            continue
        first_char = kanji[0]
        file_key = f"{ord(first_char):04X}"

        if file_key not in groups:
            groups[file_key] = {}
        groups[file_key][kanji] = readings

    return groups


def write_output_files(groups: dict[str, dict[str, list[str]]]) -> None:
    """グループ化されたデータをJSONファイルとして出力

    Args:
        groups: {16進コードポイント: {漢字: [読み]}} の辞書
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    total_written = 0
    for file_key, surnames in sorted(groups.items()):
        output_path = OUTPUT_DIR / f"{file_key}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(surnames, f, ensure_ascii=False, indent=2)
        total_written += len(surnames)

    print(f"  出力完了: {len(groups)} ファイル、合計 {total_written} エントリー")
    print(f"  出力先: {OUTPUT_DIR}")


def verify_sample() -> None:
    """サンプル検証: 山 → 5C71.json に山田が含まれるかチェック"""
    sample_char = "山"
    expected_key = f"{ord(sample_char):04X}"
    sample_file = OUTPUT_DIR / f"{expected_key}.json"

    print(f"\n検証: '{sample_char}' → {expected_key}.json")
    if sample_file.exists():
        with open(sample_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "山田" in data:
            print(f"  OK: 山田 の読み = {data['山田']}")
        else:
            print("  警告: 山田 が見つかりません")
        print(f"  ファイル内エントリー数: {len(data)}")
    else:
        print(f"  エラー: {sample_file} が存在しません")


def main() -> None:
    print("=== namedicデータ変換 ===\n")

    # ステップ1: 全ファイル読み込み
    merged = load_namedic_files()

    # ステップ2: 1文字目でグループ化
    print("\nグループ化中...")
    groups = group_by_first_char(merged)
    print(f"  グループ数: {len(groups)}")

    # ステップ3: ファイル出力
    print("\nファイル出力中...")
    write_output_files(groups)

    # ステップ4: サンプル検証
    verify_sample()

    print("\n変換完了!")


if __name__ == "__main__":
    main()
