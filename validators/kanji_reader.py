"""漢字→読み変換モジュール

漢字の氏名から想定される読み（ひらがな）を取得する。
複数の読み候補を返し、辞書にない場合は単漢字に分解して推定する。

姓データはLambdaコンテナの生存期間中モジュールレベルでキャッシュし、
漢字1文字目のUnicodeコードポイント別ファイルから遅延読み込みする。
"""

import json
from pathlib import Path
from typing import List, Tuple, Dict, Optional


# モジュールレベルキャッシュ（Lambdaコンテナの生存期間中保持）
# {16進コードポイント: {漢字: [読み]}} 例: {"5C71": {"山田": ["やまだ"]}}
_surname_cache: Dict[str, Dict[str, List[str]]] = {}


class KanjiReader:
    """漢字から読みを取得するクラス"""

    def __init__(self, dictionary_path: Optional[str] = None):
        """初期化

        Args:
            dictionary_path: 辞書ファイルのパス。Noneの場合はデフォルトパスを使用
        """
        package_dir = Path(__file__).parent.parent

        if dictionary_path is None:
            dictionary_path = package_dir / "data" / "name_readings.json"

        self._surnames_dir = package_dir / "data" / "surnames"
        self._load_dictionary(dictionary_path)

    def _load_dictionary(self, path: Path) -> None:
        """辞書ファイルを読み込む（given_names と single_kanji のみ）"""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self._given_names: Dict[str, List[str]] = data.get("given_names", {})
        self._single_kanji: Dict[str, List[str]] = data.get("single_kanji", {})

    def _get_surnames_for_char(self, first_char: str) -> Dict[str, List[str]]:
        """漢字1文字目に対応するファイルを遅延読み込み

        モジュールレベルキャッシュを使用するため、同一コンテナ内での
        2回目以降の呼び出しはファイルI/Oなしで返る。

        Args:
            first_char: 漢字の1文字目

        Returns:
            {漢字: [読み]} の辞書（該当ファイルが存在しない場合は空辞書）
        """
        file_key = f"{ord(first_char):04X}"
        if file_key not in _surname_cache:
            path = self._surnames_dir / f"{file_key}.json"
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    _surname_cache[file_key] = json.load(f)
            else:
                _surname_cache[file_key] = {}
        return _surname_cache[file_key]

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

        if is_surname:
            # 分散ファイルから姓を遅延読み込み
            surnames = self._get_surnames_for_char(kanji[0])
            if kanji in surnames:
                return surnames[kanji].copy(), True
        else:
            # 名の辞書を検索
            if kanji in self._given_names:
                return self._given_names[kanji].copy(), True

        # 反対側の辞書でも検索（姓名は重複することがある）
        if is_surname:
            if kanji in self._given_names:
                return self._given_names[kanji].copy(), True
        else:
            # 名として見つからない場合は姓辞書も検索
            surnames = self._get_surnames_for_char(kanji[0])
            if kanji in surnames:
                return surnames[kanji].copy(), True

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
