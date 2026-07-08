"""
Crypto Spread Parser — Configuration
"""

# Биржи для мониторинга (публичные данные, без API ключей)
EXCHANGES = [
    "binance",
    "bybit",
    "mexc",
    "kucoin",
    "htx",       # ex-Huobi
    "gate",      # Gate.io
    "okx",
    "bitget",
]

# Торговые пары для мониторинга
# Формат: BASE/QUOTE
PAIRS = [
    # Основные (мало спредов, но для полноты)
    "BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT",

    # Обнаруженные спредовые пары (discover_fast.py, 2026-04-10)
    "ARDR/USDT", "ASM/USDT", "BDX/USDT", "BEAM/USDT",
    "BRISE/USDT", "BULLA/USDT", "BZZ/USDT", "CHEQ/USDT",
    "CHILLGUY/USDT", "DATA/USDT", "DCR/USDT",
    "DGB/USDT", "DNX/USDT", "EDGE/USDT", "ELA/USDT",
    "EPT/USDT", "FLM/USDT", "FUN/USDT",
    "GCOIN/USDT", "GFI/USDT", "GME/USDT",
    "IDEX/USDT", "LUNC/USDT", "MLN/USDT",
    "MOVE/USDT", "OAS/USDT", "OPUL/USDT",
    "PAWS/USDT", "PEPECOIN/USDT", "PERP/USDT",
    "PORT3/USDT", "PUFFER/USDT",
    "RVV/USDT", "SCRT/USDT",
    "STOS/USDT", "STRK/USDT",
    "TARA/USDT", "TRVL/USDT",
    "UNFI/USDT", "UP/USDT",
    "USTC/USDT", "VANRY/USDT",
    "WXT/USDT", "YALA/USDT", "YFII/USDT",
    "ZEX/USDT", "ZK/USDT",
    "ARC/USDT", "TOWER/USDT",
]

# Пары-мусор: разные токены с одинаковым тикером на разных биржах
# Исключаем из алертов
BLACKLISTED_PAIRS = {
    "VON/USDT", "ELON/USDT", "TROLL/USDT", "U/USDT", "X/USDT",
    "IRON/USDT", "GF/USDT", "DUCK/USDT", "ANON/USDT", "DEFI/USDT",
    "RWA/USDT", "NC/USDT", "PIT/USDT", "POWER/USDT", "SPARKLET/USDT",
    "STREAM/USDT", "AB/USDT", "ALEX/USDT", "AO/USDT", "ARTY/USDT",
    "ATR/USDT", "DEAI/USDT", "GUA/USDT", "MANEKI/USDT", "MGO/USDT",
    "MIGGLES/USDT", "MOODENGETH/USDT", "NODL/USDT", "PZP/USDT",
    "REKTCOIN/USDT", "RMV/USDT", "SIREN/USDT", "TADA/USDT",
    "TBC/USDT", "UDS/USDT", "ULTIMA/USDT", "UNION/USDT", "UQC/USDT",
    "WOD/USDT", "CHIRP/USDT", "ITHACA/USDT",
    # Разные токены на разных биржах (спред фейковый)
    "FUN/USDT", "EDGE/USDT", "WXT/USDT", "ASM/USDT", "UP/USDT",
    "ZK/USDT", "VANRY/USDT", "SCRT/USDT", "DGB/USDT", "ARC/USDT",
    "DCR/USDT", "BULLA/USDT", "GCOIN/USDT", "OPUL/USDT", "BDX/USDT",
    "BEAM/USDT", "TARA/USDT", "ZEX/USDT",
}

# Макс спред — если больше, считаем фейковым (разные токены)
MAX_SPREAD_PCT = 25.0

# Минимальный чистый спред (%) для алерта (после вычета комиссий)
MIN_NET_SPREAD_PCT = 0.5

# Комиссии бирж (taker fee %) — приблизительные для публичных уровней
EXCHANGE_FEES = {
    "binance":  0.10,
    "bybit":    0.10,
    "mexc":     0.10,
    "kucoin":   0.10,
    "htx":      0.20,
    "gate":     0.15,
    "okx":      0.10,
    "bitget":   0.10,
}

# Интервал сканирования (секунды)
SCAN_INTERVAL = 8

# Telegram Bot API — надёжная отправка алертов
import os
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID", "0"))

# Кулдаун: не спамить одним и тем же спредом (секунды)
ALERT_COOLDOWN = 300  # 5 минут

# Минимальный объём (24h USD) на бирже для пары, чтобы не ловить мусор
MIN_VOLUME_USD = 50_000

# Логирование
LOG_FILE = "/root/crypto-spread-parser/scanner.log"
