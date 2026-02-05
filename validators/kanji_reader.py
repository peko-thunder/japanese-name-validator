"""漢字→読み変換モジュール

漢字の氏名から想定される読み（ひらがな）を取得する。
複数の読み候補を返し、辞書にない場合は単漢字に分解して推定する。
"""

import json
from pathlib import Path
from typing import List, Tuple, Dict, Optional


class KanjiReader:
    """漢字から読みを取得するクラス"""

    def __init__(self, dictionary_path: Optional[str] = None):
        """初期化

        Args:
            dictionary_path: 辞書ファイルのパス。Noneの場合はデフォルトパスを使用
        """
        if dictionary_path is None:
            # パッケージからの相対パスで辞書を探す
            package_dir = Path(__file__).parent.parent
            dictionary_path = package_dir / "data" / "name_readings.json"

        self._load_dictionary(dictionary_path)

    def _load_dictionary(self, path: Path) -> None:
        """辞書ファイルを読み込む"""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self._surnames: Dict[str, List[str]] = data.get("surnames", {})
        self._given_names: Dict[str, List[str]] = data.get("given_names", {})
        self._single_kanji: Dict[str, List[str]] = data.get("single_kanji", {})

    def get_readings(self, kanji: str, is_surname: bool = True) -> Tuple[List[str], bool]:
        """漢字から読み候補を取得

        Args:
            kanji: 漢字文字列
            is_surname: 姓の場合True、名の場合False

        Returns:
            (読み候補リスト, 辞書で見つかったかどうか)
            辞書で見つからなかった場合、空リストとFalseを返す
        """
        if not kanji:
            return [], False

        # まず完全一致で検索
        dict_to_search = self._surnames if is_surname else self._given_names
        if kanji in dict_to_search:
            return dict_to_search[kanji].copy(), True

        # 反対側の辞書でも検索（姓名は重複することがある）
        other_dict = self._given_names if is_surname else self._surnames
        if kanji in other_dict:
            return other_dict[kanji].copy(), True

        # 単漢字分解で読みを推定
        readings = self._decompose_and_read(kanji)
        if readings:
            return readings, False  # 推定なのでFalse

        return [], False

    def _decompose_and_read(self, kanji: str) -> List[str]:
        """漢字を単漢字に分解して読みを推定

        Args:
            kanji: 漢字文字列

        Returns:
            推定された読み候補のリスト
        """
        if not kanji:
            return []

        # 各漢字の読み候補を取得
        char_readings: List[List[str]] = []
        for char in kanji:
            if char in self._single_kanji:
                char_readings.append(self._single_kanji[char])
            else:
                # 辞書にない文字がある場合は推定不可
                return []

        # 読みの組み合わせを生成（最大10個に制限）
        return self._combine_readings(char_readings, max_combinations=10)

    def _combine_readings(
        self, char_readings: List[List[str]], max_combinations: int = 10
    ) -> List[str]:
        """各文字の読み候補を組み合わせる

        Args:
            char_readings: 各文字の読み候補リスト
            max_combinations: 最大組み合わせ数

        Returns:
            組み合わせられた読みのリスト
        """
        if not char_readings:
            return []

        # 組み合わせを生成
        result = char_readings[0].copy()

        for i in range(1, len(char_readings)):
            new_result = []
            for prefix in result:
                for suffix in char_readings[i]:
                    combined = prefix + suffix
                    new_result.append(combined)
                    if len(new_result) >= max_combinations:
                        return new_result
            result = new_result

        return result[:max_combinations]

    def get_surname_readings(self, kanji: str) -> Tuple[List[str], bool]:
        """姓の読みを取得（便利メソッド）"""
        return self.get_readings(kanji, is_surname=True)

    def get_given_name_readings(self, kanji: str) -> Tuple[List[str], bool]:
        """名の読みを取得（便利メソッド）"""
        return self.get_readings(kanji, is_surname=False)
