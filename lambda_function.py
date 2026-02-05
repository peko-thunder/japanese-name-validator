"""AWS Lambda ハンドラ

TOEIC申込み用 漢字氏名・ローマ字整合性チェッカーのエントリーポイント。
"""

import json
from typing import Any, Dict

from validators import NameMatcher


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda関数のエントリーポイント

    Args:
        event: API Gatewayからのイベント（bodyに入力JSON）
        context: Lambda実行コンテキスト

    Returns:
        API Gateway形式のレスポンス
    """
    try:
        # イベントボディのパース
        body = _parse_event_body(event)

        # 必須パラメータの検証
        required_fields = ["kanji_sei", "kanji_mei", "romaji_sei", "romaji_mei"]
        missing_fields = [f for f in required_fields if f not in body or not body[f]]

        if missing_fields:
            return _error_response(
                400,
                f"必須パラメータが不足しています: {', '.join(missing_fields)}",
            )

        # 入力値の取得
        kanji_sei = str(body["kanji_sei"]).strip()
        kanji_mei = str(body["kanji_mei"]).strip()
        romaji_sei = str(body["romaji_sei"]).strip()
        romaji_mei = str(body["romaji_mei"]).strip()

        # 空文字チェック
        if not all([kanji_sei, kanji_mei, romaji_sei, romaji_mei]):
            return _error_response(400, "空の値が含まれています")

        # バリデーション実行
        matcher = NameMatcher()
        result = matcher.validate(kanji_sei, kanji_mei, romaji_sei, romaji_mei)

        return _success_response(result.to_dict())

    except json.JSONDecodeError:
        return _error_response(400, "無効なJSON形式です")
    except Exception as e:
        return _error_response(500, f"内部エラー: {str(e)}")


def _parse_event_body(event: Dict[str, Any]) -> Dict[str, Any]:
    """イベントボディをパースする

    Args:
        event: Lambda イベント

    Returns:
        パースされたボディ
    """
    # API Gateway経由の場合
    if "body" in event:
        body = event["body"]
        if isinstance(body, str):
            return json.loads(body)
        return body

    # 直接呼び出しの場合
    return event


def _success_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """成功レスポンスを生成

    Args:
        data: レスポンスデータ

    Returns:
        API Gateway形式のレスポンス
    """
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json; charset=utf-8",
        },
        "body": json.dumps(data, ensure_ascii=False),
    }


def _error_response(status_code: int, message: str) -> Dict[str, Any]:
    """エラーレスポンスを生成

    Args:
        status_code: HTTPステータスコード
        message: エラーメッセージ

    Returns:
        API Gateway形式のレスポンス
    """
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json; charset=utf-8",
        },
        "body": json.dumps({"error": message}, ensure_ascii=False),
    }


# ローカルテスト用
if __name__ == "__main__":
    test_event = {
        "kanji_sei": "山田",
        "kanji_mei": "太郎",
        "romaji_sei": "YAMADA",
        "romaji_mei": "TARO",
    }
    result = lambda_handler(test_event, None)
    print(json.dumps(json.loads(result["body"]), indent=2, ensure_ascii=False))
