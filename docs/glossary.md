# dfint-ja 用語集・翻訳方針

翻訳者（人・AI）はこのファイルに従って訳語と文体を揃えてください。

## 文体

- **UIのラベル・ボタン・メニュー**: 簡潔な体言止め（例: `Settings` → `設定`、`Create new world` → `新しい世界を創造`）。
- **説明文・ヘルプ・確認メッセージ**: です・ます調（例: `Are you sure?` → `よろしいですか？`）。
- **ドワーフや住民の思考・台詞（I / my / we で始まる文）**: 常体の話し言葉（例: `I must press on!` → `進み続けなければ！`）。
- **性格・状態の記述（lowercase の断片: "is quick to anger" など）**: 常体の説明（`すぐに怒る`）。
- 句読点は全角（、。！？「」）。ただし英数字・記号・トークンはそのまま半角。
- 長すぎる訳は避ける。画面の幅が限られるので、意味が通る範囲で短く。

## 守ること

- `[C:7:0:0]` `[B]` `[P]` `[R]` `[KEY:3]` `[NAME]` `%s` `%d` などのトークンは**一字一句そのまま**残す。位置は日本語の語順に合わせて動かしてよい。
- 先頭・末尾の空白、末尾のコロン `:` は原文どおり残す。
- 数字・単位・固有の略号（FPS, Z, DF など）はそのまま。
- 意味が不明な内部文字列（関数名、ファイル名、`SAND_RED_RAMP...` のようなID）は**原文のまま**出力する。

## 基本用語

訳語は日本語Wiki（https://wikiwiki.jp/dwarffort/）に揃えています。Wikiの訳語の一覧は `translations/wiki-terms.tsv`、既存の訳を置き換えた規則は `translations/term-rules.tsv` です。新しく訳すときも、この表と `wiki-terms.tsv` に従ってください。

| 英語 | 訳語 |
|---|---|
| dwarf / dwarves | ドワーフ |
| fortress / fort | 要塞 |
| elf / human / goblin / kobold | エルフ / 人間 / ゴブリン / コボルド |
| civilization | 文明 |
| embark | 入植 |
| expedition | 遠征隊 |
| site | 拠点 |
| world | 世界 |
| world generation | 世界生成 |
| region | 地域 |
| biome | バイオーム |
| cavern | 洞窟 |
| z-level / level | 階層 |
| magma | マグマ |
| adamantine | アダマンタイン |
| stockpile | 倉庫 |
| workshop | 工房 |
| furnace / smelter | 炉 / 精錬所 |
| zone | ゾーン |
| burrow | 巣穴 |
| designation / designate | 指定 / 指定する（メニュー名の Designations は「設計」） |
| job / task | 作業 |
| work order | 作業指示 |
| labor | 労働 |
| skill | スキル |
| attribute | 属性 |
| hauling | 運搬 |
| mining / miner | 採掘 / 鉱夫 |
| woodcutting / woodcutter | 伐採 / 木こり |
| farming / farm plot | 農耕 / 農地 |
| pasture | 放牧地 |
| brewing | 醸造 |
| smoothing / engraving | 平滑化 / 彫刻 |
| fortification | 防護壁 |
| construction | 建設 |
| building / building menu | 建物 / 建築メニュー |
| citizen / resident / visitor | 市民 / 住民 / 訪問者 |
| migrant | 移民 |
| pet / livestock | ペット / 家畜 |
| squad / military | 小隊 / 軍事 |
| peasant | 田舎者 |
| noble / administrator | 貴族 / 管理者 |
| justice | 懲罰 |
| mayor / manager / bookkeeper / broker | 市長 / 支配人 / 簿記 / 取引係 |
| hammerer / champion / chief medical dwarf / monarch | 執行人 / 勇士 / 医師団長 / 国王 |
| expedition leader | 遠征隊長 |
| sheriff / captain of the guard | 保安官 / 警邏隊長 |
| militia commander / militia captain | 司令官 / 部隊長 |
| baron / count / duke / king / queen | 男爵 / 伯爵 / 公爵 / 国王 / 女王 |
| caravan / trader / merchant | キャラバン / 商人 / 商人 |
| liaison / diplomat | 連絡係 / 外交官 |
| siege / siege engine / invasion / ambush | 攻城戦 / 兵器 / 侵攻 / 待ち伏せ |
| strange mood | 奇妙な気分 |
| artifact | アーティファクト |
| tantrum | かんしゃく |
| megabeast / forgotten beast / titan | 巨獣 / 忘れられし獣 / タイタン |
| demon / vampire / werebeast / necromancer | 悪魔 / 吸血鬼 / 獣人 / 死霊術師 |
| legends | 伝説 |
| adventurer / adventure mode | 冒険者 / 冒険モード |
| fortress mode | 要塞モード |
| arena | アリーナ |
| historical figure | 歴史上の人物 |
| entity | 勢力 |
| guild / guildhall / temple / tavern / library / hospital | ギルド / ギルドホール / 神殿 / 酒場 / 図書館 / 病院 |
| barracks / dormitory / dining hall | 兵舎 / 共同寝室 / 食堂 |
| unit | ユニット |
| creature | 生物 |
| item | アイテム |
| quality: well-crafted / finely-crafted / superior / exceptional / masterful / masterwork | 良品 / 優良品 / 高級品 / 特級品 / 名品 / 傑作 |
| skill level: dabbling / novice / adequate / competent / skilled / proficient / talented / adept / expert / professional / accomplished / great / master / high master / grand master / legendary | 生かじり / 未熟者 / 十分 / 優秀 / 熟練 / 達人 / 有能 / 名人 / 専門家 / プロ / 熟達 / 偉大 / マスター / ハイマスター / グランドマスター / 伝説的 |
| workshops | 木工房 / 石工房 / 工芸所 / 鍛冶場 / 精錬所 / 炭焼き場 / 醸造所 / 調理場 / 精肉所 / なめし革工房 / 革工房 / 機織場 / 仕立て屋 / 染色場 / 農芸工房 / 魚加工所 / 宝石工房 / 機械工房 / 弓工房 / 兵器開発所 / 灰工房 / ガラス溶鉱炉 / 窯（英語名は wiki-terms.tsv） |

## 物・素材

| 英語 | 訳語 |
|---|---|
| bar | 延べ棒 |
| block | ブロック |
| boulder | 丸石 |
| rough gem | 原石 |
| log / wood | 丸太 / 木材 |
| bin / barrel / bag / bucket / large pot | 収納箱 / 樽 / 袋 / バケツ / 壺 |
| door / hatch / floodgate | 扉 / ハッチ / 水門 |
| bed / table / chair / throne | ベッド / テーブル / 椅子 / 玉座 |
| cabinet / chest / coffer / box | キャビネット / 宝箱 / 小箱 / 箱 |
| armor stand / weapon rack | 鎧立て / 武器立て |
| statue / coffin / slab | 彫像 / 棺桶 / 平板 |
| mechanism / lever / pressure plate | 仕掛け / レバー / 感圧板 |
| potash | 肥料 |
| cage / chain / rope | 檻 / 鎖 / ロープ |
| iron / steel / copper / bronze / silver / gold | 鉄 / 鋼 / 銅 / 青銅 / 銀 / 金 |
| stone / rock | 石 / 岩 |
| leather / cloth / silk / wool / yarn | 革 / 布 / 絹 / 羊毛 / 毛糸 |
| bone / shell / horn / ivory / tooth | 骨 / 殻 / 角 / 象牙 / 歯 |
| glass / clay / sand | ガラス / 粘土 / 砂 |
| drink / alcohol / ale / beer / wine / rum / mead | 酒 / アルコール / エール / ビール / ワイン / ラム酒 / 蜂蜜酒 |

## 生物名

- 身近な動物は漢字（犬・猫・馬・牛・豚・羊・熊・狼・鹿・猪・鷲・鷹・鶏・兎・蛇・鼠）、それ以外はカタカナ（ヤギ、ラマ、アルパカ、ワタリガラス）。
- 架空の生物は一般的なファンタジー訳（ユニコーン、グリフォン、ドラゴン、ヒドラ、ロック鳥）。
- 子供の呼び名（puppy, calf, kitten...）は「子犬」「子牛」「子猫」、一般的な形は「〜の子」。
- 雄・雌の呼び名（bull, cow, ram, ewe...）は「雄牛」「雌牛」「雄羊」「雌羊」、一般的な形は「〜（雄）」「〜（雌）」。
- 「X man / X woman」型の動物人間は規則で自動生成（`{X}男` / `{X}女`）するので、基本語だけ訳す。

## 植物・食べ物

- 作物・植物名はカタカナまたは一般的な和名（plump helmet → プランプヘルメット、cave wheat → 洞窟小麦、pig tail → ピッグテイル）。
- `X seed` → `Xの種`、`X leaf` → `Xの葉`、`X flower` → `Xの花`、`X wood` → `X材`。
