# 테마별 주식 사전 등록 데이터 (국내 + 해외)
# 형식: {"name": 종목명, "code": 종목코드, "themes": [관련 테마 키워드]}
# 이 데이터는 서버 기동 시 DB에 멱등하게(ON CONFLICT DO NOTHING) 삽입된다.

ALL_THEME_STOCK_SEED: list[dict] = [
    # ══════════════════════════════════════════════════════════════════════
    # 국내 주식
    # ══════════════════════════════════════════════════════════════════════

    # ── 반도체 ────────────────────────────────────────────────────────────
    {"name": "삼성전자",         "code": "005930", "themes": ["반도체", "IT"]},
    {"name": "SK하이닉스",       "code": "000660", "themes": ["반도체"]},
    {"name": "리노공업",         "code": "058470", "themes": ["반도체"]},
    {"name": "한미반도체",       "code": "042700", "themes": ["반도체"]},
    {"name": "원익IPS",          "code": "240810", "themes": ["반도체"]},
    {"name": "에스에프에이",     "code": "056190", "themes": ["반도체"]},
    {"name": "피에스케이",       "code": "319660", "themes": ["반도체"]},
    {"name": "HPSP",             "code": "403870", "themes": ["반도체"]},
    {"name": "이오테크닉스",     "code": "039030", "themes": ["반도체"]},
    {"name": "주성엔지니어링",   "code": "036930", "themes": ["반도체"]},
    {"name": "유진테크",         "code": "084370", "themes": ["반도체"]},
    {"name": "테스",             "code": "095610", "themes": ["반도체"]},
    {"name": "동진쎄미켐",       "code": "005290", "themes": ["반도체"]},
    {"name": "솔브레인",         "code": "357780", "themes": ["반도체"]},
    {"name": "SK스퀘어",         "code": "402340", "themes": ["반도체", "IT"]},

    # ── IT ────────────────────────────────────────────────────────────────
    {"name": "카카오",           "code": "035720", "themes": ["IT"]},
    {"name": "NAVER",            "code": "035420", "themes": ["IT"]},
    {"name": "삼성SDS",          "code": "018260", "themes": ["IT"]},
    {"name": "SK텔레콤",         "code": "017670", "themes": ["IT"]},
    {"name": "KT",               "code": "030200", "themes": ["IT"]},
    {"name": "크래프톤",         "code": "259960", "themes": ["IT"]},
    {"name": "엔씨소프트",       "code": "036570", "themes": ["IT"]},
    {"name": "넷마블",           "code": "251270", "themes": ["IT"]},
    {"name": "LG CNS",           "code": "064400", "themes": ["IT"]},
    {"name": "카카오페이",       "code": "377300", "themes": ["IT"]},
    {"name": "더존비즈온",       "code": "012510", "themes": ["IT"]},
    {"name": "NHN",              "code": "181710", "themes": ["IT"]},
    {"name": "펄어비스",         "code": "263750", "themes": ["IT"]},
    {"name": "컴투스",           "code": "078340", "themes": ["IT"]},
    {"name": "위메이드",         "code": "112040", "themes": ["IT"]},
    {"name": "LG유플러스",       "code": "032640", "themes": ["IT"]},
    {"name": "KT&G",             "code": "033780", "themes": ["IT"]},

    # ── 바이오 ────────────────────────────────────────────────────────────
    {"name": "삼성바이오로직스", "code": "207940", "themes": ["바이오"]},
    {"name": "셀트리온",         "code": "068270", "themes": ["바이오"]},
    {"name": "유한양행",         "code": "000100", "themes": ["바이오"]},
    {"name": "한미약품",         "code": "128940", "themes": ["바이오"]},
    {"name": "종근당",           "code": "185750", "themes": ["바이오"]},
    {"name": "녹십자",           "code": "006280", "themes": ["바이오"]},
    {"name": "HLB",              "code": "028300", "themes": ["바이오"]},
    {"name": "알테오젠",         "code": "196170", "themes": ["바이오"]},
    {"name": "리가켐바이오",     "code": "141080", "themes": ["바이오"]},
    {"name": "에스티팜",         "code": "237690", "themes": ["바이오"]},
    {"name": "보령",             "code": "003850", "themes": ["바이오"]},
    {"name": "동아에스티",       "code": "170900", "themes": ["바이오"]},
    {"name": "JW중외제약",       "code": "001060", "themes": ["바이오"]},
    {"name": "광동제약",         "code": "009290", "themes": ["바이오"]},
    {"name": "대웅제약",         "code": "069620", "themes": ["바이오"]},
    {"name": "오스코텍",         "code": "039200", "themes": ["바이오"]},

    # ── 2차전지 ───────────────────────────────────────────────────────────
    {"name": "LG에너지솔루션",  "code": "373220", "themes": ["2차전지"]},
    {"name": "삼성SDI",         "code": "006400", "themes": ["2차전지"]},
    {"name": "SK이노베이션",    "code": "096770", "themes": ["2차전지", "에너지"]},
    {"name": "에코프로비엠",    "code": "247540", "themes": ["2차전지"]},
    {"name": "에코프로",        "code": "086520", "themes": ["2차전지"]},
    {"name": "포스코퓨처엠",    "code": "003670", "themes": ["2차전지"]},
    {"name": "엘앤에프",        "code": "066970", "themes": ["2차전지"]},
    {"name": "천보",            "code": "278280", "themes": ["2차전지"]},
    {"name": "엔켐",            "code": "348370", "themes": ["2차전지"]},
    {"name": "동화기업",        "code": "025900", "themes": ["2차전지"]},
    {"name": "솔루스첨단소재",  "code": "336370", "themes": ["2차전지"]},
    {"name": "코스모신소재",    "code": "005070", "themes": ["2차전지"]},
    {"name": "나노신소재",      "code": "121600", "themes": ["2차전지"]},

    # ── 금융 ──────────────────────────────────────────────────────────────
    {"name": "KB금융",          "code": "105560", "themes": ["금융"]},
    {"name": "신한지주",        "code": "055550", "themes": ["금융"]},
    {"name": "하나금융지주",    "code": "086790", "themes": ["금융"]},
    {"name": "우리금융지주",    "code": "316140", "themes": ["금융"]},
    {"name": "메리츠금융지주",  "code": "138040", "themes": ["금융"]},
    {"name": "삼성생명",        "code": "032830", "themes": ["금융"]},
    {"name": "삼성화재",        "code": "000810", "themes": ["금융"]},
    {"name": "카카오뱅크",      "code": "323410", "themes": ["금융", "IT"]},
    {"name": "기업은행",        "code": "024110", "themes": ["금융"]},
    {"name": "BNK금융지주",     "code": "138930", "themes": ["금융"]},
    {"name": "DGB금융지주",     "code": "139130", "themes": ["금융"]},
    {"name": "한국금융지주",    "code": "071050", "themes": ["금융"]},
    {"name": "미래에셋증권",    "code": "006800", "themes": ["금융"]},
    {"name": "삼성증권",        "code": "016360", "themes": ["금융"]},
    {"name": "NH투자증권",      "code": "005940", "themes": ["금융"]},
    {"name": "키움증권",        "code": "039490", "themes": ["금융"]},
    {"name": "DB손해보험",      "code": "005830", "themes": ["금융"]},
    {"name": "현대해상",        "code": "001450", "themes": ["금융"]},

    # ── 방산 ──────────────────────────────────────────────────────────────
    {"name": "한화에어로스페이스", "code": "012450", "themes": ["방산"]},
    {"name": "한국항공우주",    "code": "047810", "themes": ["방산"]},
    {"name": "LIG넥스원",       "code": "079550", "themes": ["방산"]},
    {"name": "한화시스템",      "code": "272210", "themes": ["방산"]},
    {"name": "현대로템",        "code": "064350", "themes": ["방산"]},
    {"name": "한화오션",        "code": "042660", "themes": ["방산", "조선"]},
    {"name": "HD현대중공업",    "code": "329180", "themes": ["방산", "조선"]},
    {"name": "한화",            "code": "000880", "themes": ["방산"]},
    {"name": "풍산",            "code": "103140", "themes": ["방산"]},
    {"name": "SNT모티브",       "code": "064960", "themes": ["방산"]},
    {"name": "빅텍",            "code": "065440", "themes": ["방산"]},
    {"name": "이오시스템",      "code": "110860", "themes": ["방산"]},
    {"name": "휴니드",          "code": "005870", "themes": ["방산"]},
    {"name": "켄코아에어로스페이스", "code": "274090", "themes": ["방산"]},
    {"name": "현대위아",        "code": "011210", "themes": ["방산", "자동차"]},

    # ── 에너지 ────────────────────────────────────────────────────────────
    {"name": "한국전력",        "code": "015760", "themes": ["에너지"]},
    {"name": "한국가스공사",    "code": "036460", "themes": ["에너지"]},
    {"name": "두산에너빌리티",  "code": "034020", "themes": ["에너지"]},
    {"name": "씨에스윈드",      "code": "112610", "themes": ["에너지"]},
    {"name": "GS",              "code": "078930", "themes": ["에너지"]},
    {"name": "S-Oil",           "code": "010950", "themes": ["에너지"]},
    {"name": "HD현대에너지솔루션", "code": "322000", "themes": ["에너지"]},
    {"name": "SK가스",          "code": "018670", "themes": ["에너지"]},
    {"name": "한국쉘석유",      "code": "002960", "themes": ["에너지"]},

    # ── 소비재 ────────────────────────────────────────────────────────────
    {"name": "이마트",          "code": "139480", "themes": ["소비재"]},
    {"name": "롯데쇼핑",        "code": "023530", "themes": ["소비재"]},
    {"name": "현대백화점",      "code": "069960", "themes": ["소비재"]},
    {"name": "BGF리테일",       "code": "282330", "themes": ["소비재"]},
    {"name": "아모레퍼시픽",    "code": "090430", "themes": ["소비재"]},
    {"name": "LG생활건강",      "code": "051900", "themes": ["소비재"]},
    {"name": "오리온",          "code": "271560", "themes": ["소비재"]},
    {"name": "CJ제일제당",      "code": "097950", "themes": ["소비재"]},
    {"name": "롯데제과",        "code": "280360", "themes": ["소비재"]},
    {"name": "농심",            "code": "004370", "themes": ["소비재"]},
    {"name": "하이트진로",      "code": "000080", "themes": ["소비재"]},
    {"name": "오비맥주",        "code": "009140", "themes": ["소비재"]},
    {"name": "GS리테일",        "code": "007070", "themes": ["소비재"]},
    {"name": "신세계",          "code": "004170", "themes": ["소비재"]},
    {"name": "호텔신라",        "code": "008770", "themes": ["소비재"]},
    {"name": "코스맥스",        "code": "044820", "themes": ["소비재"]},
    {"name": "한국콜마",        "code": "161890", "themes": ["소비재"]},

    # ── 자동차 ────────────────────────────────────────────────────────────
    {"name": "현대차",          "code": "005380", "themes": ["자동차"]},
    {"name": "기아",            "code": "000270", "themes": ["자동차"]},
    {"name": "현대모비스",      "code": "012330", "themes": ["자동차"]},
    {"name": "HL만도",          "code": "204320", "themes": ["자동차"]},
    {"name": "한온시스템",      "code": "018880", "themes": ["자동차"]},
    {"name": "현대오토에버",    "code": "307950", "themes": ["자동차"]},
    {"name": "서연이화",        "code": "200880", "themes": ["자동차"]},
    {"name": "모트렉스",        "code": "118990", "themes": ["자동차"]},

    # ── 조선 ──────────────────────────────────────────────────────────────
    {"name": "HD한국조선해양",  "code": "009540", "themes": ["조선"]},
    {"name": "삼성중공업",      "code": "010140", "themes": ["조선"]},
    {"name": "HD현대미포",      "code": "010620", "themes": ["조선"]},
    {"name": "현대힘스",        "code": "347700", "themes": ["조선"]},

    # ── 화학 ──────────────────────────────────────────────────────────────
    {"name": "LG화학",          "code": "051910", "themes": ["화학", "2차전지"]},
    {"name": "롯데케미칼",      "code": "011170", "themes": ["화학"]},
    {"name": "금호석유",        "code": "011780", "themes": ["화학"]},
    {"name": "효성첨단소재",    "code": "298050", "themes": ["화학"]},
    {"name": "SKC",             "code": "011790", "themes": ["화학", "2차전지"]},
    {"name": "한화솔루션",      "code": "009830", "themes": ["화학", "에너지"]},
    {"name": "OCI",             "code": "010060", "themes": ["화학", "에너지"]},  # 오씨아이

    # ── 철강 ──────────────────────────────────────────────────────────────
    {"name": "POSCO홀딩스",     "code": "005490", "themes": ["철강"]},
    {"name": "현대제철",        "code": "004020", "themes": ["철강"]},
    {"name": "동국제강",        "code": "460860", "themes": ["철강"]},
    {"name": "고려아연",        "code": "010130", "themes": ["철강", "2차전지"]},
    {"name": "세아베스틸지주",  "code": "001430", "themes": ["철강"]},

    # ── 건설 ──────────────────────────────────────────────────────────────
    {"name": "삼성물산",        "code": "028260", "themes": ["건설"]},
    {"name": "현대건설",        "code": "000720", "themes": ["건설"]},
    {"name": "GS건설",          "code": "006360", "themes": ["건설"]},
    {"name": "대우건설",        "code": "047040", "themes": ["건설"]},
    {"name": "DL이앤씨",        "code": "375500", "themes": ["건설"]},
    {"name": "HDC현대산업개발", "code": "294870", "themes": ["건설"]},

    # ── 엔터 ──────────────────────────────────────────────────────────────
    {"name": "HYBE",            "code": "352820", "themes": ["엔터"]},
    {"name": "SM엔터테인먼트",  "code": "041510", "themes": ["엔터"]},
    {"name": "JYP엔터테인먼트", "code": "035900", "themes": ["엔터"]},
    {"name": "YG엔터테인먼트",  "code": "122870", "themes": ["엔터"]},
    {"name": "CJ ENM",          "code": "035760", "themes": ["엔터"]},
    {"name": "스튜디오드래곤",  "code": "253450", "themes": ["엔터"]},

    # ══════════════════════════════════════════════════════════════════════
    # 해외 주식 (티커 코드 사용)
    # ══════════════════════════════════════════════════════════════════════

    # ── 미국 빅테크 ──────────────────────────────────────────────────────
    {"name": "Apple",           "code": "AAPL",  "themes": ["미국 빅테크"]},
    {"name": "Microsoft",       "code": "MSFT",  "themes": ["미국 빅테크"]},
    {"name": "Alphabet (Google)", "code": "GOOGL", "themes": ["미국 빅테크"]},
    {"name": "Amazon",          "code": "AMZN",  "themes": ["미국 빅테크"]},
    {"name": "Meta",            "code": "META",  "themes": ["미국 빅테크"]},
    {"name": "Netflix",         "code": "NFLX",  "themes": ["미국 빅테크"]},
    {"name": "Salesforce",      "code": "CRM",   "themes": ["미국 빅테크"]},
    {"name": "Adobe",           "code": "ADBE",  "themes": ["미국 빅테크"]},
    {"name": "Oracle",          "code": "ORCL",  "themes": ["미국 빅테크"]},
    {"name": "Palantir",        "code": "PLTR",  "themes": ["미국 빅테크"]},
    {"name": "Snowflake",       "code": "SNOW",  "themes": ["미국 빅테크"]},
    {"name": "ServiceNow",      "code": "NOW",   "themes": ["미국 빅테크"]},

    # ── 미국 반도체 ───────────────────────────────────────────────────────
    {"name": "NVIDIA",          "code": "NVDA",  "themes": ["미국 반도체"]},
    {"name": "AMD",             "code": "AMD",   "themes": ["미국 반도체"]},
    {"name": "Intel",           "code": "INTC",  "themes": ["미국 반도체"]},
    {"name": "Qualcomm",        "code": "QCOM",  "themes": ["미국 반도체"]},
    {"name": "Broadcom",        "code": "AVGO",  "themes": ["미국 반도체"]},
    {"name": "TSMC",            "code": "TSM",   "themes": ["미국 반도체"]},
    {"name": "Applied Materials", "code": "AMAT", "themes": ["미국 반도체"]},
    {"name": "ASML",            "code": "ASML",  "themes": ["미국 반도체"]},
    {"name": "Texas Instruments", "code": "TXN", "themes": ["미국 반도체"]},
    {"name": "Micron Technology", "code": "MU",  "themes": ["미국 반도체"]},
    {"name": "Lam Research",    "code": "LRCX",  "themes": ["미국 반도체"]},
    {"name": "KLA Corporation", "code": "KLAC",  "themes": ["미국 반도체"]},
    {"name": "Marvell Technology", "code": "MRVL", "themes": ["미국 반도체"]},
    {"name": "Arm Holdings",    "code": "ARM",   "themes": ["미국 반도체"]},

    # ── 미국 금융 ─────────────────────────────────────────────────────────
    {"name": "JPMorgan Chase",  "code": "JPM",   "themes": ["미국 금융"]},
    {"name": "Goldman Sachs",   "code": "GS",    "themes": ["미국 금융"]},
    {"name": "Morgan Stanley",  "code": "MS",    "themes": ["미국 금융"]},
    {"name": "Bank of America", "code": "BAC",   "themes": ["미국 금융"]},
    {"name": "Berkshire Hathaway", "code": "BRK-B", "themes": ["미국 금융"]},
    {"name": "Visa",            "code": "V",     "themes": ["미국 금융"]},
    {"name": "Mastercard",      "code": "MA",    "themes": ["미국 금융"]},
    {"name": "American Express", "code": "AXP",  "themes": ["미국 금융"]},
    {"name": "BlackRock",       "code": "BLK",   "themes": ["미국 금융"]},
    {"name": "Citigroup",       "code": "C",     "themes": ["미국 금융"]},
    {"name": "Wells Fargo",     "code": "WFC",   "themes": ["미국 금융"]},
    {"name": "PayPal",          "code": "PYPL",  "themes": ["미국 금융"]},

    # ── 미국 바이오 ───────────────────────────────────────────────────────
    {"name": "Eli Lilly",       "code": "LLY",   "themes": ["미국 바이오"]},
    {"name": "Johnson & Johnson", "code": "JNJ", "themes": ["미국 바이오"]},
    {"name": "Pfizer",          "code": "PFE",   "themes": ["미국 바이오"]},
    {"name": "Moderna",         "code": "MRNA",  "themes": ["미국 바이오"]},
    {"name": "AbbVie",          "code": "ABBV",  "themes": ["미국 바이오"]},
    {"name": "Merck",           "code": "MRK",   "themes": ["미국 바이오"]},
    {"name": "Bristol-Myers Squibb", "code": "BMY", "themes": ["미국 바이오"]},
    {"name": "Amgen",           "code": "AMGN",  "themes": ["미국 바이오"]},
    {"name": "Biogen",          "code": "BIIB",  "themes": ["미국 바이오"]},
    {"name": "Regeneron",       "code": "REGN",  "themes": ["미국 바이오"]},
    {"name": "Gilead Sciences", "code": "GILD",  "themes": ["미국 바이오"]},
    {"name": "Intuitive Surgical", "code": "ISRG", "themes": ["미국 바이오"]},

    # ── 미국 전기차·에너지 ────────────────────────────────────────────────
    {"name": "Tesla",           "code": "TSLA",  "themes": ["미국 전기차·에너지"]},
    {"name": "Rivian",          "code": "RIVN",  "themes": ["미국 전기차·에너지"]},
    {"name": "Lucid Motors",    "code": "LCID",  "themes": ["미국 전기차·에너지"]},
    {"name": "ChargePoint",     "code": "CHPT",  "themes": ["미국 전기차·에너지"]},
    {"name": "ExxonMobil",      "code": "XOM",   "themes": ["미국 전기차·에너지"]},
    {"name": "Chevron",         "code": "CVX",   "themes": ["미국 전기차·에너지"]},
    {"name": "NextEra Energy",  "code": "NEE",   "themes": ["미국 전기차·에너지"]},
    {"name": "First Solar",     "code": "FSLR",  "themes": ["미국 전기차·에너지"]},
    {"name": "Enphase Energy",  "code": "ENPH",  "themes": ["미국 전기차·에너지"]},

    # ── 미국 소비재·유통 ──────────────────────────────────────────────────
    {"name": "Walmart",         "code": "WMT",   "themes": ["미국 소비재·유통"]},
    {"name": "Costco",          "code": "COST",  "themes": ["미국 소비재·유통"]},
    {"name": "Target",          "code": "TGT",   "themes": ["미국 소비재·유통"]},
    {"name": "Nike",            "code": "NKE",   "themes": ["미국 소비재·유통"]},
    {"name": "Starbucks",       "code": "SBUX",  "themes": ["미국 소비재·유통"]},
    {"name": "McDonald's",      "code": "MCD",   "themes": ["미국 소비재·유통"]},
    {"name": "Coca-Cola",       "code": "KO",    "themes": ["미국 소비재·유통"]},
    {"name": "PepsiCo",         "code": "PEP",   "themes": ["미국 소비재·유통"]},
    {"name": "Procter & Gamble", "code": "PG",   "themes": ["미국 소비재·유통"]},

    # ── 중국·홍콩 ─────────────────────────────────────────────────────────
    {"name": "Alibaba",         "code": "BABA",  "themes": ["중국·홍콩"]},
    {"name": "Tencent",         "code": "0700.HK", "themes": ["중국·홍콩"]},
    {"name": "JD.com",          "code": "JD",    "themes": ["중국·홍콩"]},
    {"name": "Baidu",           "code": "BIDU",  "themes": ["중국·홍콩"]},
    {"name": "PDD Holdings",    "code": "PDD",   "themes": ["중국·홍콩"]},
    {"name": "Meituan",         "code": "3690.HK", "themes": ["중국·홍콩"]},
    {"name": "BYD",             "code": "1211.HK", "themes": ["중국·홍콩"]},
    {"name": "CATL",            "code": "300750", "themes": ["중국·홍콩", "2차전지"]},
    {"name": "Xiaomi",          "code": "1810.HK", "themes": ["중국·홍콩"]},
    {"name": "NIO",             "code": "NIO",   "themes": ["중국·홍콩"]},
]


DEFENSE_STOCK_SEED: list[dict] = [
    # ── 항공 / 전투기 ───────────────────────────────────────────────
    {"name": "한화에어로스페이스", "code": "012450", "themes": ["전투기", "미사일", "엔진", "방산"]},
    {"name": "한국항공우주",    "code": "047810", "themes": ["전투기", "항공", "헬기", "방산"]},
    {"name": "켄코아에어로스페이스", "code": "274090", "themes": ["항공", "우주", "부품", "방산"]},
    {"name": "아스트",          "code": "067390", "themes": ["항공", "부품", "방산"]},
    # ── 유도무기 / 미사일 ───────────────────────────────────────────
    {"name": "LIG넥스원",       "code": "079550", "themes": ["미사일", "방공", "유도무기", "방산"]},
    # ── 레이더 / 전자전 ─────────────────────────────────────────────
    {"name": "한화시스템",      "code": "272210", "themes": ["레이더", "전자전", "방공", "방산"]},
    {"name": "빅텍",            "code": "065440", "themes": ["전자전", "통신", "방산"]},
    # ── 전차 / 장갑차 ───────────────────────────────────────────────
    {"name": "현대로템",        "code": "064350", "themes": ["전차", "장갑차", "방산"]},
    {"name": "현대위아",        "code": "011210", "themes": ["자주포", "전차", "방산"]},
    # ── 함정 / 잠수함 ───────────────────────────────────────────────
    {"name": "한화오션",        "code": "042660", "themes": ["함정", "잠수함", "방산"]},
    {"name": "HD현대중공업",    "code": "329180", "themes": ["함정", "방산"]},
    # ── 탄약 / 화약 ─────────────────────────────────────────────────
    {"name": "한화",            "code": "000880", "themes": ["화약", "탄약", "방산"]},
    {"name": "풍산",            "code": "103140", "themes": ["탄약", "화약", "방산"]},
    # ── 개인화기 / 소화기 ───────────────────────────────────────────
    {"name": "SNT모티브",       "code": "064960", "themes": ["소총", "개인화기", "방산"]},
    # ── 광학 / 항법 ─────────────────────────────────────────────────
    {"name": "이오시스템",      "code": "110860", "themes": ["광학", "항법", "방산"]},
    # ── 통신 ────────────────────────────────────────────────────────
    {"name": "휴니드",          "code": "005870", "themes": ["통신", "방산"]},
]
