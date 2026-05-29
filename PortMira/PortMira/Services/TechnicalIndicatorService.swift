import Foundation

// MARK: - Result type

struct IndicatorResult: Identifiable {
    let id:          String   // asset id
    let name:        String
    let ticker:      String
    let rsi:         Double?
    let rsiContext:  String
    let macd:        Double?
    let macdSignal:  Double?
    let macdHist:    Double?
    let macdContext: String
}

// MARK: - Service

actor TechnicalIndicatorService {

    // MARK: Fetch 3-month daily closes from Yahoo Finance

    func fetchCloses(ticker: String) async throws -> [Double] {
        let end   = Int(Date().timeIntervalSince1970)
        let start = end - 90 * 86400
        let urlStr = "https://query1.finance.yahoo.com/v8/finance/chart/\(ticker)?interval=1d&period1=\(start)&period2=\(end)"
        guard let url = URL(string: urlStr) else { return [] }
        var req = URLRequest(url: url, timeoutInterval: 15)
        req.setValue("Mozilla/5.0", forHTTPHeaderField: "User-Agent")
        let (data, _) = try await URLSession.shared.data(for: req)

        struct Resp: Decodable {
            struct Chart: Decodable {
                struct Result: Decodable {
                    struct Indicators: Decodable {
                        struct Quote: Decodable { let close: [Double?]? }
                        let quote: [Quote]
                    }
                    let indicators: Indicators
                }
                let result: [Result]?
            }
            let chart: Chart
        }

        let resp = try JSONDecoder().decode(Resp.self, from: data)
        return resp.chart.result?.first?.indicators.quote.first?.close?.compactMap { $0 } ?? []
    }

    // MARK: RSI (period = 14)

    nonisolated func calcRSI(_ closes: [Double], period: Int = 14) -> Double? {
        guard closes.count > period else { return nil }
        var gains: [Double] = []
        var losses: [Double] = []
        for i in 1..<closes.count {
            let diff = closes[i] - closes[i - 1]
            gains.append(max(diff, 0))
            losses.append(max(-diff, 0))
        }
        // Initial average
        var avgGain = gains.prefix(period).reduce(0, +) / Double(period)
        var avgLoss = losses.prefix(period).reduce(0, +) / Double(period)
        // Wilder smoothing
        for i in period..<gains.count {
            avgGain = (avgGain * Double(period - 1) + gains[i]) / Double(period)
            avgLoss = (avgLoss * Double(period - 1) + losses[i]) / Double(period)
        }
        guard avgLoss != 0 else { return 100.0 }
        let rs = avgGain / avgLoss
        let raw = 100.0 - (100.0 / (1.0 + rs))
        return (raw * 10).rounded() / 10
    }

    // MARK: MACD (fast=12, slow=26, signal=9)

    nonisolated func calcMACD(
        _ closes: [Double],
        fast: Int = 12, slow: Int = 26, signal: Int = 9
    ) -> (macd: Double?, signal: Double?, hist: Double?) {
        guard closes.count >= slow + signal else { return (nil, nil, nil) }

        // Seed EMAs from the average of the first `span` bars, then iterate from index `span`
        func ema(_ data: [Double], span: Int) -> [Double] {
            guard data.count >= span, span > 0 else { return [] }
            let k = 2.0 / Double(span + 1)
            let seed = data.prefix(span).reduce(0, +) / Double(span)
            var result = [seed]
            for i in span..<data.count {
                let prev = result[result.count - 1]
                result.append(data[i] * k + prev * (1 - k))
            }
            return result
        }

        let emaFast  = ema(closes, span: fast)
        let emaSlow  = ema(closes, span: slow)
        // Align: emaFast has (count - fast + 1) elements seeded at index fast,
        // emaSlow has (count - slow + 1) elements seeded at index slow.
        // Both cover from their respective seed index to end; take the common tail.
        let macdLine   = zip(emaFast.suffix(emaSlow.count), emaSlow).map { $0 - $1 }
        let signalLine = ema(macdLine, span: signal)
        let hist       = zip(macdLine.suffix(signalLine.count), signalLine).map { $0 - $1 }

        // Inline rounding (× 10000 → round → ÷ 10000) avoids a helper that Swift 6
        // would infer as @MainActor when declared private/fileprivate at file scope.
        return (
            macdLine.last.map   { ($0 * 10000).rounded() / 10000 },
            signalLine.last.map { ($0 * 10000).rounded() / 10000 },
            hist.last.map       { ($0 * 10000).rounded() / 10000 }
        )
    }

    // MARK: Context strings

    nonisolated func rsiContext(_ rsi: Double?) -> String {
        guard let r = rsi else { return "" }
        if r >= 70 { return "短期偏超買" }
        if r <= 30 { return "短期偏超賣" }
        if r >= 60 { return "偏強" }
        if r <= 40 { return "偏弱" }
        return "中性"
    }

    nonisolated func macdContext(_ macd: Double?, _ signal: Double?, _ hist: Double?) -> String {
        guard let h = hist, let m = macd, let s = signal else { return "" }
        if h > 0 && m > s { return "MACD 多頭排列" }
        if h < 0 && m < s { return "MACD 空頭排列" }
        if h > 0           { return "動能轉強" }
        return "動能轉弱"
    }

    // MARK: Fetch all eligible assets

    func fetchAll(assets: [Asset]) async -> [IndicatorResult] {
        let eligible = assets.filter {
            ["stock", "stock_tw", "etf", "crypto", "commodity"].contains($0.category.rawValue)
            && !($0.ticker ?? "").isEmpty
        }

        return await withTaskGroup(of: IndicatorResult?.self) { group in
            for asset in eligible {
                group.addTask {
                    let ticker = asset.category == .crypto
                        ? self.cryptoToYahoo(asset.ticker ?? "")
                        : (asset.ticker ?? "")
                    guard !ticker.isEmpty,
                          let closes = try? await self.fetchCloses(ticker: ticker),
                          !closes.isEmpty
                    else { return nil }

                    let rsi               = self.calcRSI(closes)
                    let (macd, sig, hist) = self.calcMACD(closes)
                    return IndicatorResult(
                        id:          asset.id,
                        name:        asset.name,
                        ticker:      ticker,
                        rsi:         rsi,
                        rsiContext:  self.rsiContext(rsi),
                        macd:        macd,
                        macdSignal:  sig,
                        macdHist:    hist,
                        macdContext: self.macdContext(macd, sig, hist)
                    )
                }
            }
            var results: [IndicatorResult] = []
            for await r in group {
                if let r { results.append(r) }
            }
            return results.sorted { $0.name < $1.name }
        }
    }

    // MARK: Crypto ticker normalisation → Yahoo Finance format (BTC-USD)

    nonisolated private func cryptoToYahoo(_ id: String) -> String {
        // Already in Yahoo format (e.g. "BTC-USD")
        if id.uppercased().hasSuffix("-USD") || id.uppercased().hasSuffix("-USDT") { return id.uppercased() }
        // Legacy CoinGecko name fallback
        let map: [String: String] = [
            "bitcoin": "BTC-USD", "ethereum": "ETH-USD", "binancecoin": "BNB-USD",
            "cardano": "ADA-USD", "solana": "SOL-USD", "ripple": "XRP-USD",
            "dogecoin": "DOGE-USD",
        ]
        return map[id.lowercased()] ?? "\(id.uppercased())-USD"
    }
}
