/*
 * トラックボール配線診断 (./build.sh probe でのみ組み込まれる。通常のファームウェアには入らない)
 *
 * trackball_config.h の TB_PIN_* で指定した配線 (SCLK/SDIO/nCS) を GPIO で直接操作し、
 * PMW3610 と通信できるか、動きを検出しているか、MOTION 線が届いているかを USB シリアルへ出す。
 * 確定済みの配線だけを使う。誤った組み合わせを試すとセンサーの出力と XIAO の出力が
 * ぶつかる瞬間があるため、全組み合わせの探索は TB_PROBE_SEARCH_ALL を 1 にした時だけ行う。
 */
#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/logging/log.h>

#include "../boards/shields/tws_lp_jis60/trackball_config.h"

#ifndef TB_PROBE_SEARCH_ALL
#define TB_PROBE_SEARCH_ALL 0
#endif

LOG_MODULE_REGISTER(tb_probe, LOG_LEVEL_INF);

#define PMW3610_REG_PRODUCT_ID 0x00
#define PMW3610_REG_REVISION_ID 0x01
#define PMW3610_REG_MOTION 0x02
#define PMW3610_REG_DELTA_X_L 0x03
#define PMW3610_REG_DELTA_Y_L 0x04
#define PMW3610_REG_DELTA_XY_H 0x05
#define PMW3610_REG_SQUAL 0x06
#define PMW3610_REG_SHUTTER_HIGHER 0x07
#define PMW3610_REG_SHUTTER_LOWER 0x08
#define PMW3610_REG_PIX_MAX 0x09
#define PMW3610_REG_PIX_AVG 0x0A
#define PMW3610_REG_PIX_MIN 0x0B
#define PMW3610_REG_OBSERVATION 0x2D
#define PMW3610_REG_POWER_UP_RESET 0x3A
#define PMW3610_REG_SPI_CLK_ON_REQ 0x41
#define PMW3610_SPI_CLOCK_CMD_ENABLE 0xBA
#define PMW3610_SPI_CLOCK_CMD_DISABLE 0xB5
#define PMW3610_POWERUP_CMD_RESET 0x5A
#define PMW3610_PRODUCT_ID 0x3E

#define HALF_CLK_US 50

static const struct device *const gpio0 = DEVICE_DT_GET(DT_NODELABEL(gpio0));
static const struct device *const gpio1 = DEVICE_DT_GET(DT_NODELABEL(gpio1));

/* D 番号 -> P1.xx */
static inline gpio_pin_t dpin(int d) { return (gpio_pin_t)(d + 5); }

static void write_byte(gpio_pin_t sclk, gpio_pin_t sdio, uint8_t v) {
    for (int i = 7; i >= 0; i--) {
        gpio_pin_set_raw(gpio1, sclk, 0);
        gpio_pin_set_raw(gpio1, sdio, (v >> i) & 1);
        k_busy_wait(HALF_CLK_US);
        gpio_pin_set_raw(gpio1, sclk, 1); /* センサーは立ち上がりで取り込む */
        k_busy_wait(HALF_CLK_US);
    }
}

static uint8_t read_byte(gpio_pin_t sclk, gpio_pin_t sdio) {
    uint8_t v = 0;
    for (int i = 7; i >= 0; i--) {
        gpio_pin_set_raw(gpio1, sclk, 0); /* センサーは立ち下がりで出力する */
        k_busy_wait(HALF_CLK_US);
        v |= (gpio_pin_get_raw(gpio1, sdio) & 1) << i;
        gpio_pin_set_raw(gpio1, sclk, 1);
        k_busy_wait(HALF_CLK_US);
    }
    return v;
}

static void reg_write(gpio_pin_t sclk, gpio_pin_t sdio, gpio_pin_t ncs, uint8_t reg, uint8_t val) {
    gpio_pin_configure(gpio1, sdio, GPIO_OUTPUT_HIGH);
    gpio_pin_set_raw(gpio1, ncs, 0);
    k_busy_wait(200);
    write_byte(sclk, sdio, reg | 0x80);
    write_byte(sclk, sdio, val);
    k_busy_wait(200);
    gpio_pin_set_raw(gpio1, ncs, 1);
    gpio_pin_configure(gpio1, sdio, GPIO_INPUT);
    k_busy_wait(1000);
}

static uint8_t reg_read(gpio_pin_t sclk, gpio_pin_t sdio, gpio_pin_t ncs, uint8_t reg,
                        gpio_flags_t pull) {
    gpio_pin_configure(gpio1, sdio, GPIO_OUTPUT_HIGH);
    gpio_pin_set_raw(gpio1, ncs, 0);
    k_busy_wait(200);
    write_byte(sclk, sdio, reg & 0x7F);
    gpio_pin_configure(gpio1, sdio, GPIO_INPUT | pull); /* データ線をセンサーへ明け渡す */
    k_busy_wait(300);
    uint8_t v = read_byte(sclk, sdio);
    gpio_pin_set_raw(gpio1, ncs, 1);
    gpio_pin_configure(gpio1, sdio, GPIO_INPUT);
    k_busy_wait(1000);
    return v;
}

/* 待機状態: nCS と SCLK は High を出力し続け、SDIO はプルアップ付き入力にする (線を浮かせない) */
static void release_lines(gpio_pin_t sclk, gpio_pin_t sdio, gpio_pin_t ncs) {
    gpio_pin_configure(gpio1, ncs, GPIO_OUTPUT_HIGH);
    gpio_pin_configure(gpio1, sclk, GPIO_OUTPUT_HIGH);
    gpio_pin_configure(gpio1, sdio, GPIO_INPUT | GPIO_PULL_UP);
}

static bool probe_one(int d_sclk, int d_sdio, int d_ncs, bool verbose) {
    gpio_pin_t sclk = dpin(d_sclk), sdio = dpin(d_sdio), ncs = dpin(d_ncs);

    gpio_pin_configure(gpio1, ncs, GPIO_OUTPUT_HIGH);
    gpio_pin_configure(gpio1, sclk, GPIO_OUTPUT_HIGH);
    gpio_pin_configure(gpio1, sdio, GPIO_INPUT);
    k_msleep(5);

    /* 万一レジスタのページが切り替わったまま固まっていても戻せるよう、ページ 0 を選んでからリセットする */
    reg_write(sclk, sdio, ncs, 0x7F, 0x00);
    reg_write(sclk, sdio, ncs, PMW3610_REG_POWER_UP_RESET, PMW3610_POWERUP_CMD_RESET);
    k_msleep(60);

    /* プルアップ時とプルダウン時の両方で読む。値がプルに追従するなら誰も線を駆動していない */
    uint8_t id_pu = reg_read(sclk, sdio, ncs, PMW3610_REG_PRODUCT_ID, GPIO_PULL_UP);
    uint8_t id_pd = reg_read(sclk, sdio, ncs, PMW3610_REG_PRODUCT_ID, GPIO_PULL_DOWN);
    uint8_t rev = reg_read(sclk, sdio, ncs, PMW3610_REG_REVISION_ID, GPIO_PULL_DOWN);

    release_lines(sclk, sdio, ncs);

    bool ok = (id_pu == PMW3610_PRODUCT_ID) && (id_pd == PMW3610_PRODUCT_ID);
    const char *verdict = ok ? "<== OK! sensor found"
                             : ((id_pu == 0xFF && id_pd == 0x00) ? "no response (line floating)"
                                                                 : "unexpected data");
    if (verbose) {
        LOG_INF("SCLK=D%d SDIO=D%d nCS=D%d : id(pull-up)=0x%02x id(pull-down)=0x%02x rev=0x%02x  %s",
                d_sclk, d_sdio, d_ncs, id_pu, id_pd, rev, verdict);
    }
    return ok;
}

/* リセットをかけずに製品 ID だけを読む軽いチェック。接触不良の監視に使う */
static bool link_check(int d_sclk, int d_sdio, int d_ncs) {
    gpio_pin_t sclk = dpin(d_sclk), sdio = dpin(d_sdio), ncs = dpin(d_ncs);

    gpio_pin_configure(gpio1, ncs, GPIO_OUTPUT_HIGH);
    gpio_pin_configure(gpio1, sclk, GPIO_OUTPUT_HIGH);
    uint8_t a = reg_read(sclk, sdio, ncs, PMW3610_REG_PRODUCT_ID, GPIO_PULL_UP);
    uint8_t b = reg_read(sclk, sdio, ncs, PMW3610_REG_PRODUCT_ID, GPIO_PULL_DOWN);
    uint8_t r = reg_read(sclk, sdio, ncs, PMW3610_REG_REVISION_ID, GPIO_PULL_DOWN);
    return a == PMW3610_PRODUCT_ID && b == PMW3610_PRODUCT_ID && r == 0x01;
}

/*
 * 接続の監視 (約 5 秒)。0.1 秒ごとにセンサーへ問い合わせ、応答が切れた/戻った瞬間を出す。
 * この間に配線を 1 本ずつ揺らすと、接触不良の線が分かる。
 */
static int link_monitor(int d_sclk, int d_sdio, int d_ncs) {
    int ok = 0, lost = 0;
    bool last = true;

    LOG_INF(">>> LINK MONITOR (5 seconds) <<<");
    for (int i = 0; i < 50; i++) {
        bool now = link_check(d_sclk, d_sdio, d_ncs);
        if (now) { ok++; } else { lost++; }
        if (now != last) {
            LOG_INF("  link %s", now ? "RESTORED" : "LOST  <== contact problem right now");
            last = now;
        }
        k_msleep(100);
    }
    LOG_INF("LINK MONITOR: ok=%d lost=%d of 50 %s", ok, lost,
            lost == 0 ? "(stable)" : "(UNSTABLE: intermittent contact)");
    return ok;
}

/*
 * 無応答のときの詳細。実配線の組み合わせで読んだ生の値と、MOTION 線 (NFC1) の状態を出す。
 *   id 0xff/0x00 : データ線を誰も駆動していない (SDIO/SCLK/nCS のどれかが断線、またはセンサー停止)
 *   id 0x00/0x00 : データ線が GND 側に張り付いている (ショートの疑い)
 *   id 0xff/0xff : データ線が電源側に張り付いている (ショートの疑い)
 *   それ以外      : 信号は届いているが化けている (接触が不安定)
 */
static void lost_detail(int d_sclk, int d_sdio, int d_ncs) {
    gpio_pin_t sclk = dpin(d_sclk), sdio = dpin(d_sdio), ncs = dpin(d_ncs);
    const gpio_pin_t nfc1 = 9;

    gpio_pin_configure(gpio1, ncs, GPIO_OUTPUT_HIGH);
    gpio_pin_configure(gpio1, sclk, GPIO_OUTPUT_HIGH);
    uint8_t pu = reg_read(sclk, sdio, ncs, PMW3610_REG_PRODUCT_ID, GPIO_PULL_UP);
    uint8_t pd = reg_read(sclk, sdio, ncs, PMW3610_REG_PRODUCT_ID, GPIO_PULL_DOWN);
    release_lines(sclk, sdio, ncs);

    gpio_pin_configure(gpio0, nfc1, GPIO_INPUT | GPIO_PULL_UP);
    k_msleep(2);
    int m_pu = gpio_pin_get_raw(gpio0, nfc1);
    gpio_pin_configure(gpio0, nfc1, GPIO_INPUT | GPIO_PULL_DOWN);
    k_msleep(2);
    int m_pd = gpio_pin_get_raw(gpio0, nfc1);
    gpio_pin_configure(gpio0, nfc1, GPIO_INPUT);

    const char *why;
    if (pu == 0xFF && pd == 0x00) {
        why = "data line not driven: SDIO/SCLK/nCS open, or sensor not running";
    } else if (pu == 0x00 && pd == 0x00) {
        why = "data line stuck LOW: short to GND?";
    } else if (pu == 0xFF && pd == 0xFF) {
        why = "data line stuck HIGH: short to 3V3?";
    } else {
        why = "garbled data: unstable contact";
    }
    LOG_INF("  detail: SCLK=D%d SDIO=D%d nCS=D%d id(pull-up)=0x%02x id(pull-down)=0x%02x -> %s", d_sclk,
            d_sdio, d_ncs, pu, pd, why);
    LOG_INF("  detail: MOTION(NFC1) pull-up=%d pull-down=%d", m_pu, m_pd);
}

/*
 * 線同士のショート検査。テスターの導通チェックでは「隣の線と触れている」ことは分からないので、
 * 1 本ずつ Low を出力し、プルアップした他の線が一緒に Low へ引かれないかを見る。
 */
static void short_test(int d_sclk, int d_sdio, int d_ncs) {
    const gpio_pin_t pins[3] = {dpin(d_sdio), dpin(d_sclk), dpin(d_ncs)};
    const char *names[3] = {"SDIO", "SCLK", "nCS"};
    int pu[3], pd[3];
    int shorts = 0;

    for (int i = 0; i < 3; i++) {
        gpio_pin_configure(gpio1, pins[i], GPIO_INPUT | GPIO_PULL_UP);
    }
    k_msleep(2);
    for (int i = 0; i < 3; i++) {
        pu[i] = gpio_pin_get_raw(gpio1, pins[i]);
    }
    for (int i = 0; i < 3; i++) {
        gpio_pin_configure(gpio1, pins[i], GPIO_INPUT | GPIO_PULL_DOWN);
    }
    k_msleep(2);
    for (int i = 0; i < 3; i++) {
        pd[i] = gpio_pin_get_raw(gpio1, pins[i]);
    }
    LOG_INF("  lines: pull-up SDIO=%d SCLK=%d nCS=%d | pull-down SDIO=%d SCLK=%d nCS=%d  (normal: 1 1 1 | 0 0 0)",
            pu[0], pu[1], pu[2], pd[0], pd[1], pd[2]);

    for (int drv = 0; drv < 3; drv++) {
        for (int i = 0; i < 3; i++) {
            gpio_pin_configure(gpio1, pins[i], GPIO_INPUT | GPIO_PULL_UP);
        }
        gpio_pin_configure(gpio1, pins[drv], GPIO_OUTPUT_LOW);
        k_msleep(2);
        for (int i = 0; i < 3; i++) {
            if (i != drv && pu[i] == 1 && gpio_pin_get_raw(gpio1, pins[i]) == 0) {
                LOG_INF("  SHORT: %s and %s are touching each other", names[drv], names[i]);
                shorts++;
            }
        }
    }
    if (shorts == 0) {
        LOG_INF("  shorts between SDIO/SCLK/nCS: none");
    }
    release_lines(dpin(d_sclk), dpin(d_sdio), dpin(d_ncs));
}

/*
 * 動きの検出テスト。センサーの MOTION レジスタを直接読んで「センサーがボールの動きを見ているか」を調べ、
 * 同じ瞬間に裏面パッド NFC1/NFC2 が Low になっているか (= MOTION 線が届いているか) を数える。
 * MOTION 出力の方式 (プッシュプル / オープンドレイン) に依存しないよう、パッドはプルアップして読む。
 */
static void motion_test(int d_sclk, int d_sdio, int d_ncs) {
    gpio_pin_t sclk = dpin(d_sclk), sdio = dpin(d_sdio), ncs = dpin(d_ncs);
    const gpio_pin_t nfc1 = 9, nfc2 = 10;
    int events = 0, nfc1_low_on_motion = 0, nfc2_low_on_motion = 0;
    int nfc1_low_idle = 0, nfc2_low_idle = 0, idle = 0;
    int32_t sum_x = 0, sum_y = 0;

    gpio_pin_configure(gpio1, ncs, GPIO_OUTPUT_HIGH);
    gpio_pin_configure(gpio1, sclk, GPIO_OUTPUT_HIGH);
    gpio_pin_configure(gpio1, sdio, GPIO_INPUT);
    gpio_pin_configure(gpio0, nfc1, GPIO_INPUT | GPIO_PULL_UP);
    gpio_pin_configure(gpio0, nfc2, GPIO_INPUT | GPIO_PULL_UP);

    /* ドライバと同じ手順で初期化する: リセット → 200ms → 自己診断クリア → 50ms → 自己診断結果 */
    reg_write(sclk, sdio, ncs, PMW3610_REG_POWER_UP_RESET, PMW3610_POWERUP_CMD_RESET);
    k_msleep(200);
    reg_write(sclk, sdio, ncs, PMW3610_REG_SPI_CLK_ON_REQ, PMW3610_SPI_CLOCK_CMD_ENABLE);
    reg_write(sclk, sdio, ncs, PMW3610_REG_OBSERVATION, 0x00);
    reg_write(sclk, sdio, ncs, PMW3610_REG_SPI_CLK_ON_REQ, PMW3610_SPI_CLOCK_CMD_DISABLE);
    k_msleep(50);
    uint8_t ob = reg_read(sclk, sdio, ncs, PMW3610_REG_OBSERVATION, GPIO_PULL_DOWN);
    LOG_INF("SELF TEST: observation=0x%02x (%s)", ob,
            ((ob & 0x0F) == 0x0F) ? "OK, sensor core is running" : "NG, sensor core is NOT running");

    uint8_t squal_max = 0, squal_last = 0, mot_or = 0;
    uint16_t shutter_min = 0xFFFF, shutter_max = 0;

    /* 溜まっている動きデータを一度読み捨てる */
    (void)reg_read(sclk, sdio, ncs, PMW3610_REG_MOTION, GPIO_PULL_DOWN);
    (void)reg_read(sclk, sdio, ncs, PMW3610_REG_DELTA_X_L, GPIO_PULL_DOWN);
    (void)reg_read(sclk, sdio, ncs, PMW3610_REG_DELTA_Y_L, GPIO_PULL_DOWN);
    (void)reg_read(sclk, sdio, ncs, PMW3610_REG_DELTA_XY_H, GPIO_PULL_DOWN);

    LOG_INF(">>> MOVE THE BALL NOW (20 seconds). live squal: higher = surface in focus <<<");

    uint8_t squal_sec = 0;
    int events_sec = 0;
    for (int i = 0; i < 1000; i++) { /* 20ms x 1000 = 20s */
        if (i > 0 && (i % 50) == 0) { /* 1 秒ごとのライブ表示 (距離調整用のピントメーター) */
            bool link = link_check(d_sclk, d_sdio, d_ncs);
            gpio_pin_configure(gpio1, ncs, GPIO_OUTPUT_HIGH);
            gpio_pin_configure(gpio1, sclk, GPIO_OUTPUT_HIGH);
            LOG_INF("  live %2ds: link=%s  squal=%3d  motion events=%d", i / 50,
                    link ? "OK  " : "LOST", squal_sec, events_sec);
            squal_sec = 0;
            events_sec = 0;
        }
        k_msleep(20);
        int p1 = gpio_pin_get_raw(gpio0, nfc1);
        int p2 = gpio_pin_get_raw(gpio0, nfc2);
        uint8_t mot = reg_read(sclk, sdio, ncs, PMW3610_REG_MOTION, GPIO_PULL_DOWN);

        mot_or |= mot;
        if ((i % 10) == 0) { /* 0.2 秒ごとに画像品質を読む */
            squal_last = reg_read(sclk, sdio, ncs, PMW3610_REG_SQUAL, GPIO_PULL_DOWN);
            uint16_t sh = ((uint16_t)reg_read(sclk, sdio, ncs, PMW3610_REG_SHUTTER_HIGHER, GPIO_PULL_DOWN) << 8) |
                          reg_read(sclk, sdio, ncs, PMW3610_REG_SHUTTER_LOWER, GPIO_PULL_DOWN);
            if (squal_last > squal_max) { squal_max = squal_last; }
            if (squal_last > squal_sec) { squal_sec = squal_last; }
            if (sh < shutter_min) { shutter_min = sh; }
            if (sh > shutter_max) { shutter_max = sh; }
        }

        if (mot != 0xFF && (mot & 0x80)) {
            uint8_t xl = reg_read(sclk, sdio, ncs, PMW3610_REG_DELTA_X_L, GPIO_PULL_DOWN);
            uint8_t yl = reg_read(sclk, sdio, ncs, PMW3610_REG_DELTA_Y_L, GPIO_PULL_DOWN);
            uint8_t xyh = reg_read(sclk, sdio, ncs, PMW3610_REG_DELTA_XY_H, GPIO_PULL_DOWN);
            int16_t x = (int16_t)(((xyh >> 4) << 8) | xl);
            int16_t y = (int16_t)(((xyh & 0x0F) << 8) | yl);
            if (x & 0x800) { x -= 0x1000; }
            if (y & 0x800) { y -= 0x1000; }
            if (x == 0 && y == 0) {
                continue; /* 移動量ゼロの「動き」は読み取りノイズとして数えない */
            }
            sum_x += (x < 0) ? -x : x;
            sum_y += (y < 0) ? -y : y;
            events++;
            events_sec++;
            nfc1_low_on_motion += (p1 == 0);
            nfc2_low_on_motion += (p2 == 0);
        } else {
            idle++;
            nfc1_low_idle += (p1 == 0);
            nfc2_low_idle += (p2 == 0);
        }
    }

    uint8_t pix_max = reg_read(sclk, sdio, ncs, PMW3610_REG_PIX_MAX, GPIO_PULL_DOWN);
    uint8_t pix_avg = reg_read(sclk, sdio, ncs, PMW3610_REG_PIX_AVG, GPIO_PULL_DOWN);
    uint8_t pix_min = reg_read(sclk, sdio, ncs, PMW3610_REG_PIX_MIN, GPIO_PULL_DOWN);
    LOG_INF("IMAGE: squal max=%d last=%d  shutter min=%d max=%d  pix max/avg/min=%d/%d/%d  motion-reg(or)=0x%02x",
            squal_max, squal_last, shutter_min, shutter_max, pix_max, pix_avg, pix_min, mot_or);

    release_lines(sclk, sdio, ncs);
    gpio_pin_configure(gpio0, nfc1, GPIO_INPUT);
    gpio_pin_configure(gpio0, nfc2, GPIO_INPUT);

    LOG_INF("MOTION TEST: sensor motion events=%d  |dx|=%d |dy|=%d", events, sum_x, sum_y);
    LOG_INF("MOTION TEST: NFC1 low during motion=%d/%d (idle low=%d/%d)", nfc1_low_on_motion,
            events, nfc1_low_idle, idle);
    LOG_INF("MOTION TEST: NFC2 low during motion=%d/%d (idle low=%d/%d)", nfc2_low_on_motion,
            events, nfc2_low_idle, idle);

    /* 動きの瞬間に Low になる割合 (千分率) が、静止時より十分高ければ「届いている」と判定する */
    int m1 = events ? (nfc1_low_on_motion * 1000 / events) : 0;
    int m2 = events ? (nfc2_low_on_motion * 1000 / events) : 0;
    int i1 = idle ? (nfc1_low_idle * 1000 / idle) : 0;
    int i2 = idle ? (nfc2_low_idle * 1000 / idle) : 0;
    bool nfc1_ok = nfc1_low_on_motion >= 3 && m1 >= 200 && m1 > 5 * i1;
    bool nfc2_ok = nfc2_low_on_motion >= 3 && m2 >= 200 && m2 > 5 * i2;

    if (events < 3) {
        LOG_INF("VERDICT: sensor did NOT see movement -> check lens / distance (or nothing was moved)");
    } else if (nfc1_ok) {
        LOG_INF("VERDICT: sensor tracks movement and MOTION reaches NFC1 -> wiring is complete");
    } else if (nfc2_ok) {
        LOG_INF("VERDICT: sensor tracks movement and MOTION reaches NFC2 -> set TB_PIN_MOTION_NFC 2");
    } else {
        LOG_INF("VERDICT: sensor tracks movement, but MOTION does not reach NFC1/NFC2 -> MOTION wire is open");
    }
}

static void tb_probe_thread(void *a, void *b, void *c) {
    static const int perms[6][3] = {
        /* SCLK, SDIO, nCS。先頭が trackball_config.h の配線 */
        {TB_PIN_SCLK, TB_PIN_SDIO, TB_PIN_NCS},
        {8, 10, 9}, {8, 9, 10}, {9, 10, 8}, {10, 8, 9}, {10, 9, 8},
    };
    const int n_perms = TB_PROBE_SEARCH_ALL ? 6 : 1;

    k_msleep(3000);
    if (!device_is_ready(gpio0) || !device_is_ready(gpio1)) {
        LOG_ERR("gpio not ready");
        return;
    }
    release_lines(dpin(TB_PIN_SCLK), dpin(TB_PIN_SDIO), dpin(TB_PIN_NCS));

    int found = -1;
    int lost_rounds = 0;

    for (;;) {
        if (found < 0) {
            /* 見つからない間は 1 秒ごとに問い合わせ、5 秒に 1 回だけ詳細を出す */
            for (int i = 0; i < n_perms && found < 0; i++) {
                if (probe_one(perms[i][0], perms[i][1], perms[i][2], false)) {
                    found = i;
                }
            }
            if (found < 0) {
                if ((lost_rounds++ % 5) == 0) {
                    LOG_INF("LINK LOST: sensor is not answering on SCLK=D%d SDIO=D%d nCS=D%d (%d s)",
                            TB_PIN_SCLK, TB_PIN_SDIO, TB_PIN_NCS, lost_rounds);
                    lost_detail(perms[0][0], perms[0][1], perms[0][2]);
                    short_test(perms[0][0], perms[0][1], perms[0][2]);
                }
                k_msleep(1000);
                continue;
            }
            lost_rounds = 0;
            LOG_INF("LINK OK: sensor answers with SCLK=D%d SDIO=D%d nCS=D%d", perms[found][0],
                    perms[found][1], perms[found][2]);
        }

        if (link_monitor(perms[found][0], perms[found][1], perms[found][2]) == 0) {
            found = -1; /* 完全に応答が消えたら問い合わせへ戻る */
            continue;
        }
        motion_test(perms[found][0], perms[found][1], perms[found][2]);
        k_msleep(2000);
    }
}

K_THREAD_DEFINE(tb_probe_tid, 2048, tb_probe_thread, NULL, NULL, NULL, K_LOWEST_APPLICATION_THREAD_PRIO,
                0, 0);
