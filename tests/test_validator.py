"""バリデーター全体のテスト"""

import json
import pytest

from validators.hepburn_converter import HepburnConverter
from validators.kanji_reader import KanjiReader
from validators.name_matcher import NameMatcher, CheckStatus
from lambda_function import lambda_handler


class TestHepburnConverter:
    """HepburnConverterのテスト"""

    @pytest.fixture
    def converter(self):
        return HepburnConverter()

    def test_basic_conversion(self, converter):
        """基本的なひらがな変換"""
        assert "YAMADA" in converter.convert("やまだ")
        assert "TANAKA" in converter.convert("たなか")
        assert "SUZUKI" in converter.convert("すずき")

    def test_special_characters(self, converter):
        """特殊文字の変換（し、ち、つ、ふ）"""
        assert "SHI" in converter.convert("し")
        assert "CHI" in converter.convert("ち")
        assert "TSU" in converter.convert("つ")
        assert "FU" in converter.convert("ふ")

    def test_youon(self, converter):
        """拗音の変換"""
        assert "SHA" in converter.convert("しゃ")
        assert "CHU" in converter.convert("ちゅ")
        assert "JO" in converter.convert("じょ")

    def test_sokuon(self, converter):
        """促音（っ）の変換"""
        results = converter.convert("いっぱい")
        assert any("PP" in r for r in results)

    def test_hatsuon_before_bmp(self, converter):
        """撥音（ん）がB/M/P前でMになる"""
        results = converter.convert("なんば")
        assert "NAMBA" in results

    def test_long_vowel_o(self, converter):
        """長音「おお」の揺れ"""
        results = converter.convert("おおの")
        assert "ONO" in results or "OHNO" in results or "OONO" in results

    def test_long_vowel_ou(self, converter):
        """長音「おう」の揺れ"""
        results = converter.convert("さとう")
        assert "SATO" in results or "SATOU" in results

    def test_long_vowel_uu(self, converter):
        """長音「うう」の揺れ"""
        results = converter.convert("ゆう")
        assert "YU" in results or "YUU" in results

    def test_katakana_conversion(self, converter):
        """カタカナからの変換"""
        assert "YAMADA" in converter.convert("ヤマダ")

    def test_empty_string(self, converter):
        """空文字列の処理"""
        assert converter.convert("") == [""]


class TestKanjiReader:
    """KanjiReaderのテスト"""

    @pytest.fixture
    def reader(self):
        return KanjiReader()

    def test_surname_lookup(self, reader):
        """姓の辞書検索"""
        readings, found = reader.get_surname_readings("山田")
        assert found
        assert "やまだ" in readings

    def test_given_name_lookup(self, reader):
        """名の辞書検索"""
        readings, found = reader.get_given_name_readings("太郎")
        assert found
        assert "たろう" in readings

    def test_multiple_readings(self, reader):
        """複数読みがある場合"""
        readings, found = reader.get_surname_readings("河野")
        assert found
        assert "こうの" in readings or "かわの" in readings

    def test_unknown_name(self, reader):
        """辞書にない名前"""
        readings, found = reader.get_surname_readings("珍名字")
        assert not found

    def test_single_kanji_decomposition(self, reader):
        """単漢字分解による推定"""
        # 辞書に完全一致がない場合、単漢字分解を試みる
        readings, found = reader.get_surname_readings("山本")
        # 山本は辞書にあるはず
        assert found or len(readings) > 0

    def test_empty_string(self, reader):
        """空文字列の処理"""
        readings, found = reader.get_readings("")
        assert readings == []
        assert not found


class TestNameMatcher:
    """NameMatcherのテスト"""

    @pytest.fixture
    def matcher(self):
        return NameMatcher()

    def test_valid_name(self, matcher):
        """正常系: 一致する場合"""
        result = matcher.validate("山田", "太郎", "YAMADA", "TARO")
        assert result.is_valid
        assert result.sei_check.status == CheckStatus.OK
        assert result.mei_check.status == CheckStatus.OK

    def test_valid_name_lowercase(self, matcher):
        """正常系: 小文字入力"""
        result = matcher.validate("山田", "太郎", "yamada", "taro")
        assert result.is_valid

    def test_valid_name_with_space(self, matcher):
        """正常系: スペース含む入力"""
        result = matcher.validate("山田", "太郎", "YAMA DA", "TA RO")
        assert result.is_valid

    def test_mismatch_surname(self, matcher):
        """異常系: 姓が不一致"""
        result = matcher.validate("山田", "太郎", "TANAKA", "TARO")
        assert not result.is_valid
        assert result.sei_check.status == CheckStatus.MISMATCH

    def test_mismatch_given_name(self, matcher):
        """異常系: 名が不一致"""
        result = matcher.validate("山田", "太郎", "YAMADA", "HANAKO")
        assert not result.is_valid
        assert result.mei_check.status == CheckStatus.MISMATCH

    def test_unknown_reading_passes(self, matcher):
        """警告系: 辞書にない名前は通過"""
        result = matcher.validate("珍名", "奇名", "CHINMEI", "KIMEI")
        # 辞書にない場合はUNKNOWN_READINGで通過
        assert result.is_valid
        assert len(result.warnings) > 0

    def test_long_vowel_variations_surname(self, matcher):
        """正常系: 長音揺れ（姓）"""
        # 大野 → ONO または OHNO
        result1 = matcher.validate("大野", "太郎", "ONO", "TARO")
        result2 = matcher.validate("大野", "太郎", "OHNO", "TARO")
        # 少なくとも一方は通過するはず
        assert result1.is_valid or result2.is_valid

    def test_long_vowel_variations_ou(self, matcher):
        """正常系: おう長音の揺れ"""
        # 佐藤 → SATO または SATOU
        result1 = matcher.validate("佐藤", "太郎", "SATO", "TARO")
        result2 = matcher.validate("佐藤", "太郎", "SATOU", "TARO")
        assert result1.is_valid or result2.is_valid

    def test_multiple_readings_surname(self, matcher):
        """正常系: 複数読みがある姓"""
        # 河野 → こうの or かわの
        result1 = matcher.validate("河野", "太郎", "KONO", "TARO")
        result2 = matcher.validate("河野", "太郎", "KAWANO", "TARO")
        assert result1.is_valid or result2.is_valid


class TestLambdaHandler:
    """Lambda関数のテスト"""

    def test_valid_request(self):
        """正常系: 有効なリクエスト"""
        event = {
            "kanji_sei": "山田",
            "kanji_mei": "太郎",
            "romaji_sei": "YAMADA",
            "romaji_mei": "TARO",
        }
        response = lambda_handler(event, None)
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["is_valid"]

    def test_api_gateway_format(self):
        """正常系: API Gateway形式のリクエスト"""
        event = {
            "body": json.dumps({
                "kanji_sei": "山田",
                "kanji_mei": "太郎",
                "romaji_sei": "YAMADA",
                "romaji_mei": "TARO",
            })
        }
        response = lambda_handler(event, None)
        assert response["statusCode"] == 200

    def test_missing_parameter(self):
        """異常系: パラメータ不足"""
        event = {
            "kanji_sei": "山田",
            "kanji_mei": "太郎",
            # romaji_sei と romaji_mei が不足
        }
        response = lambda_handler(event, None)
        assert response["statusCode"] == 400

    def test_empty_parameter(self):
        """異常系: 空のパラメータ"""
        event = {
            "kanji_sei": "",
            "kanji_mei": "太郎",
            "romaji_sei": "YAMADA",
            "romaji_mei": "TARO",
        }
        response = lambda_handler(event, None)
        assert response["statusCode"] == 400

    def test_invalid_json(self):
        """異常系: 無効なJSON"""
        event = {"body": "not a json"}
        response = lambda_handler(event, None)
        assert response["statusCode"] == 400

    def test_mismatch_response(self):
        """異常系: 不一致の場合のレスポンス"""
        event = {
            "kanji_sei": "山田",
            "kanji_mei": "太郎",
            "romaji_sei": "TANAKA",
            "romaji_mei": "TARO",
        }
        response = lambda_handler(event, None)
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert not body["is_valid"]
        assert body["sei_check"]["status"] == "MISMATCH"


class TestIntegration:
    """統合テスト"""

    @pytest.fixture
    def matcher(self):
        return NameMatcher()

    @pytest.mark.parametrize("kanji_sei,kanji_mei,romaji_sei,romaji_mei,expected_valid", [
        # 正常系
        ("山田", "太郎", "YAMADA", "TARO", True),
        ("佐藤", "花子", "SATO", "HANAKO", True),
        ("大野", "一郎", "ONO", "ICHIRO", True),
        ("大野", "一郎", "OHNO", "ICHIRO", True),
        ("河野", "次郎", "KONO", "JIRO", True),
        ("河野", "次郎", "KAWANO", "JIRO", True),
        ("鈴木", "健太", "SUZUKI", "KENTA", True),
        ("高橋", "美咲", "TAKAHASHI", "MISAKI", True),
        ("渡辺", "翔", "WATANABE", "SHO", True),
        # 異常系
        ("山田", "太郎", "TANAKA", "TARO", False),
        ("佐藤", "花子", "SATO", "TARAKO", False),
    ])
    def test_various_names(self, matcher, kanji_sei, kanji_mei, romaji_sei, romaji_mei, expected_valid):
        """様々な名前のテスト"""
        result = matcher.validate(kanji_sei, kanji_mei, romaji_sei, romaji_mei)
        assert result.is_valid == expected_valid, f"Failed for {kanji_sei} {kanji_mei}"
