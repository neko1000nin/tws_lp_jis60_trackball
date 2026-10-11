#!/usr/bin/env bash
# tws_lp_jis60 ファームウェアをローカルで一発ビルドするスクリプト (Docker 使用)
#
#   ./build.sh            右手(トラックボール付き)・左手・settings_reset を全部ビルド
#   ./build.sh right      右手側だけビルド (感度調整などの繰り返し用。一番速い)
#   ./build.sh left       左手側だけビルド
#   ./build.sh reset      settings_reset だけビルド
#   ./build.sh debug      右手側のログ出力付きビルド (USB シリアルにセンサーの初期化状況が出る)
#   ./build.sh probe      配線診断版 (センサーとの通信・ボールの動き・MOTION 線を調べてログに出す)
#   ./build.sh btlog      Bluetooth 動作確認版 (接続・切断・アドバタイズの状況を USB シリアルに出す)
#   ./build.sh btdiag     Bluetooth 接続制限の調査版 (btlog に安全装置 60 秒を足したもの)
#   ./build.sh update     west.yml を変更したあとにモジュールを取り直す
#   ./build.sh clean      ビルドキャッシュ(.build/)を削除
#
# 成果物は firmware/*.uf2 に出力される。
# 初回は ZMK/Zephyr の取得で数分かかる。2 回目以降は差分ビルドで速い。
set -euo pipefail

IMAGE="${ZMK_BUILD_IMAGE:-zmkfirmware/zmk-build-arm:3.5}"   # ZMK v0.3 = Zephyr 3.5
BOARD="seeeduino_xiao_ble"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK_DIR="${REPO_DIR}/.build"       # west ワークスペース (zmk, zephyr, modules ...)
OUT_DIR="${REPO_DIR}/firmware"

# ---- コンテナ内で実行される部分 -------------------------------------------
if [[ "${1:-}" == "__in_container__" ]]; then
    shift
    cd /work

    # config/west.yml をワークスペースへコピー (CI の build-user-config.yml と同じ構成)
    mkdir -p /work/config
    if ! cmp -s /repo/config/west.yml /work/config/west.yml 2>/dev/null; then
        cp /repo/config/west.yml /work/config/west.yml
        NEED_UPDATE=1
    fi
    [[ -d /work/.west ]] || { west init -l /work/config; NEED_UPDATE=1; }
    [[ -d /work/zmk/app && -d /work/zephyr ]] || NEED_UPDATE=1
    if [[ "${NEED_UPDATE:-0}" == 1 || "${FORCE_UPDATE:-0}" == 1 ]]; then
        echo "==> west update (初回/west.yml 変更時のみ)"
        west update --fetch-opt=--filter=tree:0
    fi
    west zephyr-export >/dev/null

    # patches/*.patch を ZMK 本体に当てる (未適用のものだけ。west update で戻った場合も再適用される)
    for patch in /repo/patches/zmk-*.patch; do
        [[ -f "$patch" ]] || continue
        if git -C /work/zmk apply --check --reverse "$patch" >/dev/null 2>&1; then
            continue   # 適用済み
        fi
        echo "==> applying $(basename "$patch") to zmk"
        git -C /work/zmk apply "$patch"
    done

    mkdir -p /repo/firmware
    for target in "$@"; do
        west_args=(); cmake_args=()
        case "$target" in
            right) shield="tws_lp_jis60_right rgbled_adapter"; name="tws_lp_jis60_right" ;;
            left)  shield="tws_lp_jis60_left rgbled_adapter";  name="tws_lp_jis60_left" ;;
            reset) shield="settings_reset";                    name="settings_reset" ;;
            # 右手側 + USB シリアルへのログ出力 (トラックボールが動かない時の原因調査用)
            debug) shield="tws_lp_jis60_right rgbled_adapter"; name="tws_lp_jis60_right_debug"
                   west_args=(-S zmk-usb-logging); # センサー初期化を起動 45 秒後に遅らせ、COM ポートを開き直す時間を確保する
                   cmake_args=(-DCONFIG_PMW3610_LOG_LEVEL_DBG=y -DCONFIG_PMW3610_INIT_POWER_UP_EXTRA_DELAY_MS=45000 -DCONFIG_ZMK_LOGGING_MINIMAL=y -DCONFIG_ZMK_LOG_LEVEL_WRN=y) ;;
            # 配線診断: trackball_config.h の配線でセンサーとの通信・動き・MOTION 線を調べ、USB シリアルへ出す
            probe) shield="tws_lp_jis60_right rgbled_adapter"; name="tws_lp_jis60_right_pinprobe"
                   west_args=(-S zmk-usb-logging)
                   # ZMK 本体の詳細ログ (左手側の探索など) は止め、診断の行だけが見えるようにする
                   cmake_args=(-DCONFIG_TWS_LP_JIS60_TB_PIN_PROBE=y -DDTS_EXTRA_CPPFLAGS=-DTB_PIN_PROBE -DCONFIG_ZMK_LOGGING_MINIMAL=y -DCONFIG_ZMK_LOG_LEVEL_WRN=y) ;;
            # Bluetooth の動作確認用: 右手側 + USB シリアルへ ZMK の Bluetooth ログ (接続・切断・アドバタイズ)
            btlog) shield="tws_lp_jis60_right rgbled_adapter"; name="tws_lp_jis60_right_btlog"
                   west_args=(-S zmk-usb-logging)
                   cmake_args=(-DCONFIG_ZMK_LOGGING_MINIMAL=y -DCONFIG_ZMK_LOG_LEVEL_INF=y -DCONFIG_BT_LOG_LEVEL_WRN=y) ;;
            # 接続制限の原因調査用: 動作実績のある btlog と同じ構成に、接続制限 (+ 安全装置) だけを足したもの。
            # ZMK のログは INF (接続待ち・接続・切断・暗号化の行が出る)。詳細 DBG は出さない
            btdiag) shield="tws_lp_jis60_right rgbled_adapter"; name="tws_lp_jis60_right_btdiag"
                   west_args=(-S zmk-usb-logging)
                   cmake_args=(-DCONFIG_ZMK_BLE_ADV_FILTER_ACTIVE_PROFILE=y -DCONFIG_ZMK_BLE_ADV_FILTER_FALLBACK_TIMEOUT=60
                               -DCONFIG_ZMK_LOGGING_MINIMAL=y -DCONFIG_ZMK_LOG_LEVEL_INF=y
                               -DCONFIG_BT_LOG_LEVEL_WRN=y
                               -DCONFIG_LOG_BUFFER_SIZE=8192) ;;
            *) echo "unknown target: $target" >&2; exit 2 ;;
        esac
        # 右手側には ZMK 本体へのパッチ用の設定 (接続制限) を足す。GitHub Actions ではパッチが当たらないので読み込まない
        [[ "$name" == tws_lp_jis60_right* ]] && cmake_args+=(-DEXTRA_CONF_FILE=/repo/patches/zmk-ble-adv-filter.conf)
        echo "==> building ${name}"
        west build -s zmk/app -d "/work/build/${name}" -b "${BOARD}" "${west_args[@]}" -- \
            -DZMK_CONFIG=/repo/config \
            -DSHIELD="${shield}" \
            -DZMK_EXTRA_MODULES=/repo \
            "${cmake_args[@]}"
        cp "/work/build/${name}/zephyr/zmk.uf2" "/repo/firmware/${name}-${BOARD}-zmk.uf2"
    done
    exit 0
fi

# ---- ホスト側 ---------------------------------------------------------------
targets=()
force_update=0
for arg in "$@"; do
    case "$arg" in
        right|left|reset|debug|probe|btlog|btdiag) targets+=("$arg") ;;
        all)    targets=(right left reset) ;;
        update) force_update=1 ;;
        clean)  rm -rf "${WORK_DIR}" "${OUT_DIR}"; echo "cleaned"; exit 0 ;;
        -h|--help|help) sed -n '2,16p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "unknown argument: $arg (right|left|reset|debug|probe|btlog|btdiag|all|update|clean)" >&2; exit 2 ;;
    esac
done
[[ ${#targets[@]} -gt 0 ]] || targets=(right left reset)

command -v docker >/dev/null || { echo "docker が見つかりません。Docker をインストールしてください。" >&2; exit 1; }

mkdir -p "${WORK_DIR}/home" "${OUT_DIR}"
tty_flag=(); [[ -t 1 ]] && tty_flag=(-t)

docker run --rm "${tty_flag[@]}" \
    --user "$(id -u):$(id -g)" \
    -e HOME=/work/home \
    -e FORCE_UPDATE="${force_update}" \
    -v "${REPO_DIR}:/repo" \
    -v "${WORK_DIR}:/work" \
    -w /work \
    "${IMAGE}" \
    /repo/build.sh __in_container__ "${targets[@]}"

echo
echo "==> 完了。UF2 はこちら:"
ls -1 "${OUT_DIR}"/*.uf2
