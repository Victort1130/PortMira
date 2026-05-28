HISTORICAL_EVENTS = {
    "": {"name": "自訂", "period": "", "description": "", "shocks": {"categories": {}, "fx": {}}, "hedging": []},
    "2008_financial_crisis": {
        "name": "2008 金融海嘯",
        "period": "2007-10 ~ 2009-03",
        "description": "美國次貸危機引發全球金融海嘯，股市腰斬",
        "shocks": {
            "categories": {"stock": -0.57, "stock_tw": -0.60, "etf": -0.50, "crypto": 0.0, "other": -0.20, "cash": 0.0},
            "fx": {"USD": 0.10, "EUR": -0.15, "JPY": 0.20, "GBP": -0.25}
        },
        "hedging": [
            "增持現金比例至 20-30%",
            "配置黃金 ETF (GLD) 5-10%",
            "美國長債 (TLT) 抵禦通縮",
            "避開高槓桿資產與金融股"
        ]
    },
    "2020_covid_crash": {
        "name": "2020 COVID 崩盤",
        "period": "2020-02 ~ 2020-03",
        "description": "新冠疫情引發全球股市急跌，33天內下跌超過三成",
        "shocks": {
            "categories": {"stock": -0.34, "stock_tw": -0.30, "etf": -0.32, "crypto": -0.63, "other": -0.15, "cash": 0.0},
            "fx": {"USD": 0.08, "EUR": -0.05, "JPY": 0.05, "GBP": -0.10}
        },
        "hedging": [
            "增持現金，保留流動性",
            "醫療保健股 (XLV) 相對抗跌",
            "美國短債 (SHY) 保值",
            "避免過度集中科技與旅遊業"
        ]
    },
    "2022_rate_hike": {
        "name": "2022 升息熊市",
        "period": "2022-01 ~ 2022-10",
        "description": "Fed 激進升息，科技股與加密貨幣腰斬",
        "shocks": {
            "categories": {"stock": -0.24, "stock_tw": -0.25, "etf": -0.20, "crypto": -0.77, "other": -0.10, "cash": 0.0},
            "fx": {"USD": 0.15, "EUR": -0.15, "JPY": -0.20, "GBP": -0.15}
        },
        "hedging": [
            "能源股 (XLE) 受益升息環境",
            "短天期公債或浮動利率債",
            "大幅減持高估值科技股",
            "加密貨幣倉位降至 5% 以下"
        ]
    },
    "2000_dot_com": {
        "name": "2000 科技泡沫",
        "period": "2000-03 ~ 2002-10",
        "description": "網路泡沫破裂，NASDAQ 下跌 78%，台股下跌近七成",
        "shocks": {
            "categories": {"stock": -0.49, "stock_tw": -0.68, "etf": -0.45, "crypto": 0.0, "other": -0.15, "cash": 0.0},
            "fx": {"USD": 0.05, "EUR": -0.05, "JPY": 0.05, "GBP": 0.0}
        },
        "hedging": [
            "價值股與公用事業股 (XLU) 相對強勢",
            "黃金 ETF 抗通縮保值",
            "避開高本益比成長股",
            "加速還清融資貸款"
        ]
    }
}
