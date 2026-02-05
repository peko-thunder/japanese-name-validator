"""ひらがな→ヘボン式ローマ字変換モジュール

外務省パスポート表記に準拠したヘボン式ローマ字変換を行う。
長音表記の揺れに対応するため、複数の候補を生成する。
"""

from typing import List
from itertools import product


class HepburnConverter:
    """ひらがな/カタカナをヘボン式ローマ字に変換するクラス"""

    # 基本変換テーブル（2文字以上のパターンを先に配置）
    ROMAJI_TABLE = {
        # 拗音（しゃ行）
        "しゃ": "SHA", "しゅ": "SHU", "しょ": "SHO",
        "じゃ": "JA", "じゅ": "JU", "じょ": "JO",
        # 拗音（ちゃ行）
        "ちゃ": "CHA", "ちゅ": "CHU", "ちょ": "CHO",
        "ぢゃ": "JA", "ぢゅ": "JU", "ぢょ": "JO",
        # 拗音（その他）
        "きゃ": "KYA", "きゅ": "KYU", "きょ": "KYO",
        "ぎゃ": "GYA", "ぎゅ": "GYU", "ぎょ": "GYO",
        "にゃ": "NYA", "にゅ": "NYU", "にょ": "NYO",
        "ひゃ": "HYA", "ひゅ": "HYU", "ひょ": "HYO",
        "びゃ": "BYA", "びゅ": "BYU", "びょ": "BYO",
        "ぴゃ": "PYA", "ぴゅ": "PYU", "ぴょ": "PYO",
        "みゃ": "MYA", "みゅ": "MYU", "みょ": "MYO",
        "りゃ": "RYA", "りゅ": "RYU", "りょ": "RYO",
        # 基本（あ行）
        "あ": "A", "い": "I", "う": "U", "え": "E", "お": "O",
        # 基本（か行）
        "か": "KA", "き": "KI", "く": "KU", "け": "KE", "こ": "KO",
        "が": "GA", "ぎ": "GI", "ぐ": "GU", "げ": "GE", "ご": "GO",
        # 基本（さ行）
        "さ": "SA", "し": "SHI", "す": "SU", "せ": "SE", "そ": "SO",
        "ざ": "ZA", "じ": "JI", "ず": "ZU", "ぜ": "ZE", "ぞ": "ZO",
        # 基本（た行）
        "た": "TA", "ち": "CHI", "つ": "TSU", "て": "TE", "と": "TO",
        "だ": "DA", "ぢ": "JI", "づ": "ZU", "で": "DE", "ど": "DO",
        # 基本（な行）
        "な": "NA", "に": "NI", "ぬ": "NU", "ね": "NE", "の": "NO",
        # 基本（は行）
        "は": "HA", "ひ": "HI", "ふ": "FU", "へ": "HE", "ほ": "HO",
        "ば": "BA", "び": "BI", "ぶ": "BU", "べ": "BE", "ぼ": "BO",
        "ぱ": "PA", "ぴ": "PI", "ぷ": "PU", "ぺ": "PE", "ぽ": "PO",
        # 基本（ま行）
        "ま": "MA", "み": "MI", "む": "MU", "め": "ME", "も": "MO",
        # 基本（や行）
        "や": "YA", "ゆ": "YU", "よ": "YO",
        # 基本（ら行）
        "ら": "RA", "り": "RI", "る": "RU", "れ": "RE", "ろ": "RO",
        # 基本（わ行）
        "わ": "WA", "ゐ": "I", "ゑ": "E", "を": "O",
        # 撥音
        "ん": "N",
    }

    # B/M/P で始まる音のリスト（撥音がMになる）
    BMP_SOUNDS = {"B", "M", "P"}

    # カタカナ→ひらがな変換用オフセット
    KATAKANA_START = ord("ァ")
    KATAKANA_END = ord("ヶ")
    HIRAGANA_START = ord("ぁ")

    def __init__(self):
        # 2文字パターンのリスト（長いパターンを優先するため）
        self._two_char_patterns = [k for k in self.ROMAJI_TABLE.keys() if len(k) == 2]

    def katakana_to_hiragana(self, text: str) -> str:
        """カタカナをひらがなに変換"""
        result = []
        for char in text:
            code = ord(char)
            if self.KATAKANA_START <= code <= self.KATAKANA_END:
                result.append(chr(code - self.KATAKANA_START + self.HIRAGANA_START))
            elif char == "ー":
                result.append("ー")
            else:
                result.append(char)
        return "".join(result)

    def convert(self, text: str) -> List[str]:
        """ひらがな/カタカナをヘボン式ローマ字に変換

        長音表記の揺れに対応するため、複数の候補を返す。

        Args:
            text: 変換対象の文字列（ひらがなまたはカタカナ）

        Returns:
            ローマ字候補のリスト（大文字）
        """
        if not text:
            return [""]

        # カタカナをひらがなに正規化
        hiragana = self.katakana_to_hiragana(text)

        # 変換実行
        segments = self._convert_to_segments(hiragana)

        # 組み合わせを生成（候補数を制限）
        candidates = self._generate_combinations(segments, max_candidates=10)

        return candidates

    def _convert_to_segments(self, hiragana: str) -> List[List[str]]:
        """ひらがな文字列をローマ字セグメントに変換

        各位置で可能なローマ字候補のリストを返す。
        長音の揺れがある場合、複数の候補を持つセグメントになる。
        """
        segments = []
        i = 0

        while i < len(hiragana):
            char = hiragana[i]

            # 促音（っ）の処理
            if char == "っ":
                # 次の文字の子音を重ねる
                if i + 1 < len(hiragana):
                    next_romaji = self._get_single_romaji(hiragana, i + 1)
                    if next_romaji and next_romaji[0].isalpha():
                        consonant = next_romaji[0]
                        # CHの場合はTを重ねる
                        if next_romaji.startswith("CH"):
                            consonant = "T"
                        segments.append([consonant])
                    else:
                        segments.append(["T"])
                else:
                    segments.append(["T"])
                i += 1
                continue

            # 撥音（ん）の処理
            if char == "ん":
                # 次の文字がB/M/Pで始まる場合はMに変換
                if i + 1 < len(hiragana):
                    next_romaji = self._get_single_romaji(hiragana, i + 1)
                    if next_romaji and next_romaji[0] in self.BMP_SOUNDS:
                        segments.append(["M"])
                    else:
                        segments.append(["N"])
                else:
                    segments.append(["N"])
                i += 1
                continue

            # 長音記号（ー）の処理
            if char == "ー":
                if segments:
                    # 前のセグメントの母音を伸ばす
                    last_segment = segments[-1]
                    new_segment = []
                    for variant in last_segment:
                        if variant:
                            last_vowel = self._get_last_vowel(variant)
                            if last_vowel:
                                # 長音の揺れを生成
                                new_segment.extend([
                                    variant,  # 省略形
                                    variant + last_vowel,  # 母音重ね
                                ])
                                if last_vowel == "O":
                                    new_segment.append(variant[:-1] + "OH" if variant.endswith("O") else variant + "H")
                    if new_segment:
                        segments[-1] = list(set(new_segment))
                i += 1
                continue

            # 2文字パターンの確認（拗音など）
            if i + 1 < len(hiragana):
                two_char = hiragana[i:i+2]
                if two_char in self.ROMAJI_TABLE:
                    romaji = self.ROMAJI_TABLE[two_char]
                    segments.append([romaji])
                    i += 2
                    continue

            # 1文字パターン
            if char in self.ROMAJI_TABLE:
                romaji = self.ROMAJI_TABLE[char]
                segments.append([romaji])
            else:
                # 変換できない文字はそのまま
                segments.append([char])
            i += 1

        # 長音パターンの後処理（おお、おう、うう等）
        segments = self._process_long_vowels(segments, hiragana)

        return segments

    def _get_single_romaji(self, hiragana: str, index: int) -> str:
        """指定位置の文字のローマ字を取得"""
        if index >= len(hiragana):
            return ""

        # 2文字パターンを先に確認
        if index + 1 < len(hiragana):
            two_char = hiragana[index:index+2]
            if two_char in self.ROMAJI_TABLE:
                return self.ROMAJI_TABLE[two_char]

        char = hiragana[index]
        return self.ROMAJI_TABLE.get(char, "")

    def _get_last_vowel(self, romaji: str) -> str:
        """ローマ字の最後の母音を取得"""
        vowels = "AIUEO"
        for char in reversed(romaji.upper()):
            if char in vowels:
                return char
        return ""

    def _process_long_vowels(self, segments: List[List[str]], hiragana: str) -> List[List[str]]:
        """長音パターンの揺れを処理

        おお → O / OH / OO
        おう → O / OU
        ゆう → YU / YUU
        """
        result = []
        i = 0
        h_idx = 0

        while i < len(segments):
            # ひらがなのインデックスを追跡
            current_hiragana = ""
            if h_idx < len(hiragana):
                current_hiragana = hiragana[h_idx]

            # おお パターン
            if (i + 1 < len(segments) and
                len(segments[i]) == 1 and len(segments[i+1]) == 1 and
                segments[i][0].endswith("O") and segments[i+1][0] == "O"):
                base = segments[i][0]
                result.append([
                    base,          # 省略: ONO
                    base + "O",    # 重ね: OONO
                    base[:-1] + "OH" if base.endswith("O") else base + "H",  # H表記: OHNO
                ])
                i += 2
                h_idx += 2
                continue

            # おう パターン
            if (i + 1 < len(segments) and
                len(segments[i]) == 1 and len(segments[i+1]) == 1 and
                segments[i][0].endswith("O") and segments[i+1][0] == "U"):
                base = segments[i][0]
                result.append([
                    base,          # 省略: SATO
                    base + "U",    # 重ね: SATOU
                ])
                i += 2
                h_idx += 2
                continue

            # うう パターン
            if (i + 1 < len(segments) and
                len(segments[i]) == 1 and len(segments[i+1]) == 1 and
                segments[i][0].endswith("U") and segments[i+1][0] == "U"):
                base = segments[i][0]
                result.append([
                    base,          # 省略: YU
                    base + "U",    # 重ね: YUU
                ])
                i += 2
                h_idx += 2
                continue

            # いい パターン
            if (i + 1 < len(segments) and
                len(segments[i]) == 1 and len(segments[i+1]) == 1 and
                segments[i][0].endswith("I") and segments[i+1][0] == "I"):
                base = segments[i][0]
                result.append([
                    base,          # 省略
                    base + "I",    # 重ね
                ])
                i += 2
                h_idx += 2
                continue

            result.append(segments[i])
            i += 1
            h_idx += 1

        return result

    def _generate_combinations(self, segments: List[List[str]], max_candidates: int = 10) -> List[str]:
        """セグメントの組み合わせからローマ字候補を生成"""
        if not segments:
            return [""]

        # 各セグメントから重複を除去
        unique_segments = [list(set(seg)) for seg in segments]

        # 組み合わせ数を計算
        total_combinations = 1
        for seg in unique_segments:
            total_combinations *= len(seg)

        # 組み合わせ数が多すぎる場合は制限
        if total_combinations > max_candidates:
            # 各セグメントの最初の候補のみを使用しつつ、
            # 長音揺れのあるセグメントは全候補を保持
            limited_segments = []
            for seg in unique_segments:
                if len(seg) <= 3:
                    limited_segments.append(seg)
                else:
                    limited_segments.append(seg[:3])
            unique_segments = limited_segments

        # 組み合わせを生成
        candidates = []
        for combo in product(*unique_segments):
            candidates.append("".join(combo))

        # 重複を除去
        return list(dict.fromkeys(candidates))[:max_candidates]
