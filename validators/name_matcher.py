"""整合性チェックロジック

漢字氏名とローマ字氏名の整合性を検証する。
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from .hepburn_converter import HepburnConverter
from .kanji_reader import KanjiReader


class CheckStatus(str, Enum):
    """チェック結果のステータス"""
    OK = "OK"
    MISMATCH = "MISMATCH"
    UNKNOWN_READING = "UNKNOWN_READING"


@dataclass
class NameCheckResult:
    """姓または名のチェック結果"""
    status: CheckStatus
    input: str
    expected_readings: List[str]
    expected_romaji: List[str]
    message: Optional[str] = None

    def to_dict(self) -> dict:
        """辞書形式に変換"""
        return {
            "status": self.status.value,
            "input": self.input,
            "expected_readings": self.expected_readings,
            "expected_romaji": self.expected_romaji,
            "message": self.message,
        }


@dataclass
class ValidationResult:
    """バリデーション全体の結果"""
    is_valid: bool
    sei_check: NameCheckResult
    mei_check: NameCheckResult
    warnings: List[str]

    def to_dict(self) -> dict:
        """辞書形式に変換"""
        return {
            "is_valid": self.is_valid,
            "sei_check": self.sei_check.to_dict(),
            "mei_check": self.mei_check.to_dict(),
            "warnings": self.warnings,
        }


class NameMatcher:
    """漢字氏名とローマ字氏名の整合性をチェックするクラス"""

    def __init__(
        self,
        kanji_reader: Optional[KanjiReader] = None,
        hepburn_converter: Optional[HepburnConverter] = None,
    ):
        """初期化

        Args:
            kanji_reader: 漢字読み取得クラス。Noneの場合は新規作成
            hepburn_converter: ローマ字変換クラス。Noneの場合は新規作成
        """
        self._kanji_reader = kanji_reader or KanjiReader()
        self._hepburn_converter = hepburn_converter or HepburnConverter()

    def validate(
        self,
        kanji_sei: str,
        kanji_mei: str,
        romaji_sei: str,
        romaji_mei: str,
    ) -> ValidationResult:
        """漢字氏名とローマ字氏名の整合性をチェック

        Args:
            kanji_sei: 漢字の姓
            kanji_mei: 漢字の名
            romaji_sei: ローマ字の姓
            romaji_mei: ローマ字の名

        Returns:
            ValidationResult: チェック結果
        """
        warnings: List[str] = []

        # 姓のチェック
        sei_result = self._check_name(
            kanji_sei, romaji_sei, is_surname=True
        )
        if sei_result.status == CheckStatus.UNKNOWN_READING:
            warnings.append(f"姓「{kanji_sei}」の読みが辞書にありません")

        # 名のチェック
        mei_result = self._check_name(
            kanji_mei, romaji_mei, is_surname=False
        )
        if mei_result.status == CheckStatus.UNKNOWN_READING:
            warnings.append(f"名「{kanji_mei}」の読みが辞書にありません")

        # 全体の判定
        # UNKNOWN_READINGは警告のみで通過
        is_valid = (
            sei_result.status in (CheckStatus.OK, CheckStatus.UNKNOWN_READING)
            and mei_result.status in (CheckStatus.OK, CheckStatus.UNKNOWN_READING)
        )

        return ValidationResult(
            is_valid=is_valid,
            sei_check=sei_result,
            mei_check=mei_result,
            warnings=warnings,
        )

    def _check_name(
        self, kanji: str, romaji: str, is_surname: bool
    ) -> NameCheckResult:
        """姓または名の整合性をチェック

        Args:
            kanji: 漢字
            romaji: ローマ字
            is_surname: 姓の場合True

        Returns:
            NameCheckResult: チェック結果
        """
        # 入力を正規化
        normalized_romaji = self._normalize_romaji(romaji)

        # 漢字から読みを取得
        readings, found_in_dict = self._kanji_reader.get_readings(
            kanji, is_surname=is_surname
        )

        # 辞書に読みがない場合
        if not readings:
            return NameCheckResult(
                status=CheckStatus.UNKNOWN_READING,
                input=normalized_romaji,
                expected_readings=[],
                expected_romaji=[],
                message="漢字の読みが辞書にありません",
            )

        # 読みからローマ字候補を生成
        all_romaji_candidates: List[str] = []
        for reading in readings:
            romaji_candidates = self._hepburn_converter.convert(reading)
            all_romaji_candidates.extend(romaji_candidates)

        # 重複を除去
        all_romaji_candidates = list(dict.fromkeys(all_romaji_candidates))

        # 入力ローマ字と比較
        if normalized_romaji in all_romaji_candidates:
            return NameCheckResult(
                status=CheckStatus.OK,
                input=normalized_romaji,
                expected_readings=readings,
                expected_romaji=all_romaji_candidates,
                message=None,
            )

        # 辞書にはあるが不一致の場合
        if found_in_dict:
            return NameCheckResult(
                status=CheckStatus.MISMATCH,
                input=normalized_romaji,
                expected_readings=readings,
                expected_romaji=all_romaji_candidates,
                message="入力されたローマ字が期待値と一致しません",
            )

        # 単漢字分解で推定した場合（精度が低いため警告扱い）
        return NameCheckResult(
            status=CheckStatus.UNKNOWN_READING,
            input=normalized_romaji,
            expected_readings=readings,
            expected_romaji=all_romaji_candidates,
            message="漢字の読みを推定しましたが、正確性を保証できません",
        )

    def _normalize_romaji(self, romaji: str) -> str:
        """ローマ字を正規化

        - 大文字に変換
        - 前後の空白を除去
        - 内部の空白を除去

        Args:
            romaji: 入力ローマ字

        Returns:
            正規化されたローマ字
        """
        return romaji.upper().replace(" ", "").strip()
