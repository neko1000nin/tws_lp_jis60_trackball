# Tws-Lp-Jis60 Firmware

> [!NOTE]
> このリポジトリは [b-sky-lab/tws_lp_shield_module](https://github.com/b-sky-lab/tws_lp_shield_module) の fork です。
> 右手側に PMW3610 トラックボールを追加し、マウス操作用のレイヤーなどを加えています。
> トラックボールの取り付けには追加のハードウェアが必要です。ケース (ドック) は 3D プリンタで出力する想定で、その 3D モデル (STL / STEP) と組み立て方法を [hardware/](hardware/README.md) で公開しています。
> 元のキーボードの情報は fork 元を参照してください。

## 概要
本リポジトリは [tws_lp_jis60](https://github.com/b-sky-lab/tws_lp_jis60)のファームウェアを提供するものです．

## キーマップ

キーマップは [tws_lp_jis60.keymap](boards/shields/tws_lp_jis60/tws_lp_jis60.keymap) にあり，各レイヤーの配置図がコメントで書かれています．`Fn`キーを押している間は Lower レイヤーになります．
すなわち，`Fn + 1`で`F1`が，`Fn + BS`で`Delete`が打てます．
左右の`Fn`キー同時押し (どちらから押してもよい) で Adjust レイヤーに入り，`Fn + Fn + Q`で`BT_SEL_0`が，`Fn + Fn + N`で`IND_CON`が押せます．

fork 元からは次の点を変えています．

- 最下段の配置 (下の注意を参照)．
- `:`と`英数`キーは，押しながら他のキーを押すとマウス操作になります (「マウス操作 (Mouse Layer)」の項)．
- `Fn + Fn + X`で Custom モード，`Fn + Fn + Z`で Default に戻ります (「Custom モード」の項．作者の好みに合わせた参考の設定)．
- `Fn + Fn + Q`〜`T`(`BT_SEL 0`〜`4`) は，選んだ番号以外の機器との接続を切ります (下記)．

> [!WARNING]
> **最下段のキー配置が fork 元と異なります．** fork 元では左下の端が`Ctrl`，その右が`Fn`ですが，このリポジトリでは左下の端が`Fn`，その右が`半角/全角`です．fork 元の配置に慣れている場合や，fork 元のキーキャップの配置に合わせている場合は注意してください．
> 左手側は HHKB Professional JP の最下段と同じ並びですが，右手側は HHKB とも異なります．
>
> | 最下段 (左から) | fork 元 | このリポジトリ | HHKB Professional JP |
> |---|---|---|---|
> | 左手 1 | `Ctrl` | `Fn` | Fn |
> | 左手 2 | `Fn` | `半角/全角` | 半角/全角 |
> | 左手 3 | `Win` | `Win` | ◇ (Win) |
> | 左手 4 | `Alt` | `Alt` | Alt |
> | 左手 5 | `英数` (LANG2) | `無変換` (INT5)，押しながらでマウス操作 | 無変換 |
> | 左手 6 / 右手 1 | `Space` | `Space` | Space (1 つ) |
> | 右手 2 | `かな` (LANG1) | `変換` (INT4) | 変換 |
> | 右手 3 | `Win` | `Win` | かな |
> | 右手 4 | `Alt` | `Alt` | Alt |
> | 右手 5 | `Fn` | `Fn` | Fn |
> | 右手 6〜8 | `←` `↓` `→` | `←` `↓` `→` | ← ↓ → |
>
> - `Ctrl` は 3 段目左端のものを使います (fork 元と同じ位置)．
> - fork 元の`英数`/`かな`(LANG2/LANG1) は macOS の英数/かなキーと同じコードですが，このリポジトリの`無変換`/`変換`(INT5/INT4) は Windows 向けです．macOS で使う場合は fork 元の設定に戻してください．
> - ZMK Studio でキーを変更して本体に保存してある場合は，書き込み後もその内容が優先されます．
> - HHKB の配置は [HHKB Professional JP のキー配列図](https://happyhackingkb.com/jp/products/image/leaflet/hhkb_pro_jp_keylayout.pdf) によります．

また，特殊キー略称の意味は以下の通りです．

- `BT_SEL n`: n番目のペアリング済みBluetoothデバイスに接続
    - 何もペアリングしていない番号を選んだ時は，その番号で新規ペアリング受付状態に入ります．
    - USB で PC につないでいる間は，Bluetooth の接続先に関係なくキー入力は USB 側へ送られます．
    - 切り替えと同時に，他の番号の機器との接続を切ります（登録は残ります）．また，選択中の番号の機器だけが接続できるようになっており，他の登録済み機器は接続自体ができません（`patches/` の ZMK パッチによる機能で，`build.sh` でのローカルビルド限定．「ZMK 本体へのパッチ」の項を参照）．
    - 電源投入やスリープ復帰の直後は，選択中の機器がつながるまで 5〜10 秒ほどかかります．20 秒たっても選択中の機器がつながらない場合は，その番号の機器以外も接続できる状態に自動で切り替わります（選択中の機器がつながった時点で元に戻ります）．
- `BT_CLR`: 現在接続中のBluetooth接続をペアリング削除
- `BT_CLR_ALL`: 保存済みの全てのBluetooth接続をペアリング削除
- `IND_CON`: Bluetooth接続状態をLEDで表示
    - 青: 接続中
    - 黄: ペアリング待ち
    - 赤: 切断
    - ステータスLEDの色の詳細は次を参照してください: https://github.com/caksoylar/zmk-rgbled-widget 
- `IND_BAT`: バッテリ残量をLEDで表示
    - 緑: 30%以上
    - 黄: 30~10%の間
    - 赤: 10%以下
    - ステータスLEDの色の詳細は次を参照してください: https://github.com/caksoylar/zmk-rgbled-widget 

## トラックボール (PMW3610) 対応

右手側 (セントラル) に PMW3610 センサーを追加できます。センサーを接続していなくても、キーボードとしてはそのまま動作します。

センサーを収めるケース (着脱式のドック) は 3D プリンタで出力する想定です。3D モデル (STL / STEP)、設計スクリプト、購入部品と組み立て方法は [hardware/README.md](hardware/README.md) で公開しています。

### 配線

既存のキーマトリクス (D0〜D7) は変更しません。未使用だったピンだけを使います。

| センサー基板 J1 | XIAO BLE (右手側) | nRF52840 | 備考 |
|---|---|---|---|
| VIN | 3V3 | - | 3.3V 入力 (基板上の LDO で 1.8V に降圧) |
| GND | GND | - | |
| SDIO | D8 | P1.13 | データ (MOSI/MISO 兼用の 3 線式 SPI) |
| SCLK | D9 | P1.14 | SPI クロック |
| nCS | D10 | P1.15 | チップセレクト |
| MOTION | NFC1 (裏面パッド) | P0.09 | 割り込み。overlay の `nfct-pins-as-gpios` で GPIO 化 |

D8〜D10 の割り当ては `trackball_config.h` の `TB_PIN_SDIO` / `TB_PIN_SCLK` / `TB_PIN_NCS` で変更できます。

### 動作

- ボールの動きをマウスカーソルの移動としてホストへ送ります。
- ディープスリープからの復帰はキー入力で行います (ボールを回しても復帰しません)。

### マウス操作 (Mouse Layer)

`:` キーか `英数` キーを押している間だけ Mouse Layer が有効になります。単独で押したときは、従来どおり `:` / `無変換` が入力されます (behavior は `Mouse Layer-Tap`)。

| キー | 動作 | キー | 動作 | キー | 動作 |
|---|---|---|---|---|---|
| `U` | 横スクロール 左 | `I` | 縦スクロール 上 | `O` | 横スクロール 右 |
| `J` | 左クリック | `K` | 縦スクロール 下 | `L` | 右クリック |
| `M` | ボタン 4 (戻る) | `,` | 中クリック | `.` | ボタン 5 (進む) |

- クリックは押している間ホールドされるので、`:` + `J` (または `英数` + `J`) を押したままボールを回すとドラッグできます。
- スクロールは 1 回押すと 1 ノッチ、押し続けると連続スクロールです。
- ZMK Studio では、`Mouse Layer-Tap` (レイヤー = Mouse、キー = 任意) を他のキーにも割り当てられます。スクロールは `Scroll Up` / `Scroll Down` / `Scroll Left` / `Scroll Right`、クリックは `Mouse Key Press` (MB1〜MB5) を選びます。標準の `Layer-Tap` も選べます。
- ZMK Studio で変更済みのキーは、本体に保存された内容が優先されます。

### Custom モード (Android / iPad 用・参考)

> [!NOTE]
> このモードは作者の使い方に合わせた設定で、参考として載せています。使わなければ (Fn + Fn + X を押さなければ) 他の動作には影響しません。

作者は Windows では「のどか」(Windows 用のキー配置変更ソフト) を使い、Ctrl を押しながらの Emacs 風のカーソル移動などをしています。のどかが使えない Android / iPad で同じような操作をするために、キーボード側で再現したのがこのモードです。特に `;` を Enter にしているのは作者の好みです。好みに合わない場合は、キーマップの Custom レイヤー (`cm_*`) を編集するか、ZMK Studio で変更してください。

左右の Fn を押しながら `X` で Custom モードに入り、`Z` で Default に戻ります。スリープから復帰すると Default に戻ります。

| キー | 単独 | Ctrl + | Ctrl + Shift + |
|---|---|---|---|
| `;` | Enter | `;` | `+` (JIS 配列の端末) |
| `A` | A | Home | Ctrl + A |
| `S` | S | Ctrl + F | |
| `E` / `P` / `N` / `F` / `B` | 文字 | End / ↑ / ↓ / → / ← | |
| `H` / `D` | 文字 | BackSpace / Delete | |

`英数` と `:` によるマウス操作、Fn を使う操作は、Custom モードでもすべてそのまま使えます。

### 感度・向きの調整

[boards/shields/tws_lp_jis60/trackball_config.h](boards/shields/tws_lp_jis60/trackball_config.h) を編集して、右手側だけ再ビルドします。

| 項目 | 定義 | 既定値 |
|---|---|---|
| カーソル速度 (センサー CPI, 200〜3200 / 200 刻み) | `TB_CPI` | 600 |
| カーソル速度の微調整 (MUL/DIV 倍) | `TB_SCALE_MUL` / `TB_SCALE_DIV` | 1 / 1 |
| 軸の入れ替え、画面上の左右反転、上下反転 (入れ替えが先) | `TB_SWAP_XY` / `TB_INVERT_X` / `TB_INVERT_Y` | 1 / 1 / 1 |
| 応答性優先 (電池消費増) | `TB_FORCE_AWAKE` | 0 |

## ローカルビルド

Docker があればコマンド一発でビルドできます。成果物は `firmware/*.uf2` に出力されます。

```sh
./build.sh          # 右手・左手・settings_reset を全部ビルド
./build.sh right    # 右手側だけ (感度調整の繰り返しはこれで十分)
./build.sh left     # 左手側だけ
./build.sh reset    # settings_reset だけ
./build.sh debug    # 右手側のログ出力付きビルド (USB シリアルにセンサーの初期化状況が出る)
./build.sh probe    # 配線診断版 (センサーとの通信・ボールの動き・MOTION 線を調べて USB シリアルに出す)
./build.sh btlog    # Bluetooth 動作確認版 (接続・切断の状況を USB シリアルに出す)
./build.sh update   # config/west.yml を変更した後にモジュールを取り直す
./build.sh clean    # ビルドキャッシュ (.build/) を削除
```

初回は ZMK / Zephyr の取得に数分かかります。

書き込みは、XIAO の RESET を素早く 2 回押すと PC にドライブとして現れるので、右手側には `tws_lp_jis60_right-*.uf2`、左手側には `tws_lp_jis60_left-*.uf2` をコピーします。左右の接続がおかしくなったときは、両側に `settings_reset-*.uf2` を書き込んでから戻すと初期化できます (Bluetooth の登録も消えます)。

GitHub に push すると Actions でもビルドされ、成果物 (`firmware`) をダウンロードできます。ただし下記のパッチは当たりません。

### ZMK 本体へのパッチ (実験的・ローカルビルド限定)

`patches/zmk-ble-adv-filter-active-profile.patch` は ZMK v0.3 本体への独自の改変で、公式には取り込まれていません。選択中の Bluetooth 接続先の機器だけが接続できるようにするもので、作者の環境 (XIAO nRF52840 + Windows PC + Android) でのみ動作を確認しています。起動直後の接続待ちを始め直す回避策など、原因が未解明の部分を含みます。設定は `patches/zmk-ble-adv-filter.conf` にあります。不具合が出た場合はこのファイルで `CONFIG_ZMK_BLE_ADV_FILTER_ACTIVE_PROFILE=n` にすると、元の ZMK と同じ動作に戻ります。

`patches/` にある ZMK 本体へのパッチと設定は `build.sh` が自動で当てます。GitHub Actions のビルドではどちらも使われないため、Bluetooth の接続制限は効かず、元の ZMK と同じ動作になります (それ以外の機能は同じです)。Actions でも有効にするには、ZMK を fork してパッチを取り込み、`config/west.yml` の `zmk` をその fork に向け、`patches/zmk-ble-adv-filter.conf` の内容を右手側の conf に移してください。
