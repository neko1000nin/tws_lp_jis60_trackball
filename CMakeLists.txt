# 通常ビルドでは何も追加しない。配線診断 (./build.sh probe) のときだけ診断コードを組み込む。
target_sources_ifdef(CONFIG_TWS_LP_JIS60_TB_PIN_PROBE app PRIVATE src/tb_pin_probe.c)
