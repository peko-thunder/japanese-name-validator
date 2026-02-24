/**
 * ================================================================
 * 名字読み辞書スクレイパー
 * myoji.namedic.jp → 漢字名字 + 読み方 JSONファイル生成
 * ================================================================
 *
 * 【使い方】
 *  1. Chrome で https://myoji.namedic.jp/sei/yomi_list/あ を開く
 *  2. F12 → Console タブを開く
 *  3. このスクリプト全体をコピー → Console に貼り付け → Enter
 *     → 初回はヘルプが表示されます（データ収集は開始しません）
 *
 *  4. 収集コマンドを入力:
 *     collectCurrentYomi()        ← 現在のページの文字を収集
 *     collectMultiple(['あ','い']) ← 指定した複数の文字を収集
 *     collectMultiple(ALL_YOMI)   ← 全文字を一括収集
 *
 * 【出力JSONフォーマット例】
 *  01_あ.json
 *  {
 *    "yomi": "あ",
 *    "index": "01",
 *    "totalCount": 816,
 *    "collectedAt": "2026-02-24T...",
 *    "entries": [
 *      { "kanji": "上田", "readings": ["うえだ","うえた",...], "population": "とても多い" },
 *      ...
 *    ]
 *  }
 *
 * ================================================================
 */

// ----------------------------------------------------------------
// 文字 → ファイル番号マッピング (63文字)
// ----------------------------------------------------------------
const YOMI_INDEX_MAP = {
  あ: "01",
  い: "02",
  う: "03",
  え: "04",
  お: "05",
  か: "06",
  き: "07",
  く: "08",
  け: "09",
  こ: "10",
  が: "11",
  ぎ: "12",
  ぐ: "13",
  げ: "14",
  ご: "15",
  さ: "16",
  し: "17",
  す: "18",
  せ: "19",
  そ: "20",
  ざ: "21",
  じ: "22",
  ず: "23",
  ぜ: "24",
  ぞ: "25",
  た: "26",
  ち: "27",
  つ: "28",
  て: "29",
  と: "30",
  だ: "31",
  ぢ: "32",
  づ: "33",
  で: "34",
  ど: "35",
  な: "36",
  に: "37",
  ぬ: "38",
  ね: "39",
  の: "40",
  は: "41",
  ひ: "42",
  ふ: "43",
  へ: "44",
  ほ: "45",
  ば: "46",
  び: "47",
  ぶ: "48",
  べ: "49",
  ぼ: "50",
  ま: "51",
  み: "52",
  む: "53",
  め: "54",
  も: "55",
  や: "56",
  ゆ: "57",
  よ: "58",
  ら: "59",
  り: "60",
  る: "61",
  れ: "62",
  ろ: "63",
  わ: "64",
};

// 全文字リスト（順番通り）
const ALL_YOMI = [
  "あ",
  "い",
  "う",
  "え",
  "お",
  "か",
  "き",
  "く",
  "け",
  "こ",
  "が",
  "ぎ",
  "ぐ",
  "げ",
  "ご",
  "さ",
  "し",
  "す",
  "せ",
  "そ",
  "ざ",
  "じ",
  "ず",
  "ぜ",
  "ぞ",
  "た",
  "ち",
  "つ",
  "て",
  "と",
  "だ",
  "ぢ",
  "づ",
  "で",
  "ど",
  "な",
  "に",
  "ぬ",
  "ね",
  "の",
  "は",
  "ひ",
  "ふ",
  "へ",
  "ほ",
  "ば",
  "び",
  "ぶ",
  "べ",
  "ぼ",
  "ま",
  "み",
  "む",
  "め",
  "も",
  "や",
  "ゆ",
  "よ",
  "ら",
  "り",
  "る",
  "れ",
  "ろ",
  "わ",
];

// ----------------------------------------------------------------
// 内部ユーティリティ
// ----------------------------------------------------------------

/** HTMLテキスト → エントリ配列に変換 */
function _parseTable(html) {
  const parser = new DOMParser();
  const doc = parser.parseFromString(html, "text/html");
  const rows = Array.from(doc.querySelectorAll("table tr")).slice(1); // ヘッダースキップ
  const entries = [];

  for (const row of rows) {
    const cells = Array.from(row.querySelectorAll("td"));
    if (cells.length < 2) continue;

    const kanji = cells[0].innerText.trim();
    if (!kanji) continue;

    // 読み: <a>タグから取得（なければテキストをスペース分割）
    const aLinks = cells[1].querySelectorAll("a");
    const readings =
      aLinks.length > 0
        ? Array.from(aLinks)
            .map((a) => a.innerText.trim())
            .filter(Boolean)
        : cells[1].innerText.trim().split(/\s+/).filter(Boolean);

    const population = cells[2] ? cells[2].innerText.trim() : "";
    entries.push({ kanji, readings, population });
  }
  return entries;
}

/** HTML → 最終ページ番号 */
function _getLastPage(html) {
  const parser = new DOMParser();
  const doc = parser.parseFromString(html, "text/html");
  const links = Array.from(doc.querySelectorAll("a"));

  // 「最後へ」リンクを優先
  const lastLink = links.find((a) => a.textContent.trim() === "最後へ");
  if (lastLink) {
    const m = (lastLink.getAttribute("href") || "").match(/page=(\d+)/);
    if (m) return parseInt(m[1], 10);
  }

  // フォールバック: page= 付きリンクの最大値
  const nums = links
    .map((a) => {
      const m = (a.getAttribute("href") || "").match(/page=(\d+)/);
      return m ? +m[1] : 0;
    })
    .filter((n) => n > 0);
  return nums.length > 0 ? Math.max(...nums) : 1;
}

/** JSONファイルをブラウザからダウンロード */
function _download(data, filename) {
  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: "application/json;charset=utf-8",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

const _sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// ----------------------------------------------------------------
// 1文字分を収集してダウンロード (内部処理)
// ----------------------------------------------------------------
async function _collectYomi(yomi, pageDelay) {
  const index = YOMI_INDEX_MAP[yomi];
  if (!index) throw new Error(`未定義の読み文字: "${yomi}"`);

  const baseUrl = `https://myoji.namedic.jp/sei/yomi_list/${encodeURIComponent(yomi)}`;
  const filename = `${index}_${yomi}.json`;

  // page 1
  const html1 = await fetch(baseUrl).then((r) => r.text());
  const lastPage = _getLastPage(html1);
  let all = _parseTable(html1);
  console.log(`  [${yomi}] page 1/${lastPage} → ${all.length}件`);

  // page 2 〜 lastPage
  for (let p = 2; p <= lastPage; p++) {
    await _sleep(pageDelay);
    const html = await fetch(`${baseUrl}?page=${p}`).then((r) => r.text());
    const entries = _parseTable(html);
    all = all.concat(entries);
    console.log(`  [${yomi}] page ${p}/${lastPage} → 累計 ${all.length}件`);
  }

  const result = {
    yomi,
    index,
    totalCount: all.length,
    collectedAt: new Date().toISOString(),
    entries: all,
  };

  _download(result, filename);
  console.log(`  ✅ ${filename} ダウンロード完了 (${all.length}件)`);
  return result;
}

// ----------------------------------------------------------------
// 公開 API
// ----------------------------------------------------------------

/**
 * 現在開いているページの文字を自動収集してダウンロード
 * @param {number} [pageDelay=300] - ページ間の待機時間(ms)
 */
window.collectCurrentYomi = function (pageDelay = 300) {
  const m = location.pathname.match(/yomi_list\/([^?/]+)/);
  if (!m) {
    console.error(
      "❌ 対象ページではありません。\nhttps://myoji.namedic.jp/sei/yomi_list/あ のようなURLで開いてください。",
    );
    return;
  }
  const yomi = decodeURIComponent(m[1]);
  console.log(`\n📖 「${yomi}」 収集開始...`);
  return _collectYomi(yomi, pageDelay).catch((e) =>
    console.error("❌ エラー:", e),
  );
};

/**
 * 複数の読み文字を順番に収集してダウンロード
 * @param {string[]} yomiList - 収集する読み文字の配列
 * @param {number} [pageDelay=300]  - ページ間待機(ms)
 * @param {number} [yomiDelay=1500] - 文字間待機(ms)
 */
window.collectMultiple = function (
  yomiList,
  pageDelay = 300,
  yomiDelay = 1500,
) {
  console.log(
    `\n🚀 一括収集開始: ${yomiList.length}文字 [${yomiList.join(", ")}]`,
  );
  (async () => {
    const summary = {};
    for (const yomi of yomiList) {
      console.log(`\n--- 「${yomi}」 ---`);
      try {
        const res = await _collectYomi(yomi, pageDelay);
        summary[yomi] = res.totalCount;
      } catch (e) {
        console.error(`❌ [${yomi}]:`, e.message || e);
        summary[yomi] = "ERROR";
      }
      if (yomi !== yomiList[yomiList.length - 1]) await _sleep(yomiDelay);
    }
    console.log("\n📊 ===== 収集サマリー =====");
    let total = 0;
    for (const [y, cnt] of Object.entries(summary)) {
      const idx = YOMI_INDEX_MAP[y] || "??";
      console.log(`  ${idx}_${y}.json : ${cnt}`);
      if (typeof cnt === "number") total += cnt;
    }
    console.log(`  合計: ${total}件`);
    console.log("==========================");
  })();
};

// ----------------------------------------------------------------
// 起動時ヘルプ表示
// ----------------------------------------------------------------
console.log(`
╔═══════════════════════════════════════════════════════════╗
║        名字読み辞書スクレイパー 読み込み完了              ║
╠═══════════════════════════════════════════════════════════╣
║                                                           ║
║  【1文字ずつ実行する場合（推奨）】                        ║
║  対象URLを開いてから実行:                                 ║
║    collectCurrentYomi()                                   ║
║                                                           ║
║  【複数文字を指定して一括実行】                           ║
║    collectMultiple(['あ','い','う','え','お'])             ║
║                                                           ║
║  【全文字（63文字）を一括実行】                           ║
║    collectMultiple(ALL_YOMI)                              ║
║                                                           ║
║  【オプション: ページ間待機を長めに設定】                 ║
║    collectCurrentYomi(500)        ← 500ms 待機            ║
║    collectMultiple(ALL_YOMI, 500, 2000)                   ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
`);
