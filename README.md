# Tws-Lp-Jis60 Firmware

## 概要
本リポジトリは [tws_lp_jis60](https://github.com/b-sky-lab/tws_lp_jis60)のファームウェアを提供するものです．

## キーマップ

画像最上段はデフォルトのキーマップ，中段は`Fn1`キー押下時に使えるキーのマップ，最下段は`Fn2`キー押下時に使えるキーのマップです．
すなわち，`Fn + 1`で`F1`が，`Fn + BS`で`Delete`が打てます．
左右の`Fn`キー同時押しで最下段のレイヤーに入り，`Fn(右) + Fn(左) + Q`で`BT_SEL_0`が，`Fn(右) + Fn(左) + N`で`IND_CON`が押せます．

また，特殊キー略称の意味は以下の通りです．

- `BT_SEL n`: n番目のペアリング済みBluetoothデバイスに接続
    - 何もペアリングしていない番号を選んだ時は，その番号で新規ペアリング受付状態に入ります．
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


![キーマップ](doc/images/keymap.png)


https://www.keyboard-layout-editor.com/#/gists/35fc311bae26cc121fb2835988d3a9b2

## トラックボール (PMW3610) 対応

右手側 (セントラル) に PMW3610 センサーを追加できます。センサーを接続していなくても、キーボードとしてはそのまま動作します。

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

- ボールの動きをマウスカーソルの移動としてホストへ送ります。クリックやスクロールはファームウェアでは扱いません。キーマップは従来のままです。
- ディープスリープからの復帰はキー入力で行います (ボールを回しても復帰しません)。

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
./build.sh debug    # 右手側のログ出力付きビルド (USB シリアルにセンサーの初期化状況が出る)
./build.sh probe    # 配線診断版 (D8/D9/D10 の全組み合わせでセンサーの応答を調べてログに出す)
./build.sh update   # config/west.yml を変更した後にモジュールを取り直す
./build.sh clean    # ビルドキャッシュ (.build/) を削除
```

初回は ZMK / Zephyr の取得に数分かかります。GitHub Actions でのビルドも従来どおり使えます。
