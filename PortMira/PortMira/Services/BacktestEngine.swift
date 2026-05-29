import Foundation

struct BacktestResult {
    let dates: [String]
    let portfolioValues: [Double]
    let benchmarkValues: [Double?]?
    let totalReturn: Double
    let cagr: Double
    let maxDrawdown: Double
    let assetReturns: [(name: String, ticker: String, returnPct: Double)]
    let skipped: [String]
    let benchmark: String?
}

actor BacktestEngine {

    private let cryptoTickerMap: [String: String] = [
        "bitcoin": "BTC-USD", "ethereum": "ETH-USD", "binancecoin": "BNB-USD",
        "cardano": "ADA-USD", "solana": "SOL-USD", "ripple": "XRP-USD",
        "polkadot": "DOT-USD", "dogecoin": "DOGE-USD", "avalanche-2": "AVAX-USD",
        "chainlink": "LINK-USD", "litecoin": "LTC-USD", "stellar": "XLM-USD"
    ]

    func run(assets: [Asset], startDate: Date, endDate: Date, benchmark: String?) async throws -> BacktestResult {
        var backTestAssets: [(asset: Asset, ticker: String)] = []
        var skipped: [String] = []

        for a in assets {
            if let t = yahooTicker(for: a) {
                backTestAssets.append((a, t))
            } else {
                skipped.append(a.name)
            }
        }

        guard !backTestAssets.isEmpty else {
            throw BacktestError.noTickers
        }

        let allTickers = backTestAssets.map(\.ticker) + (benchmark.map { [$0] } ?? [])
        var historicalPrices: [String: [(date: Date, close: Double)]] = [:]

        await withTaskGroup(of: (String, [(Date, Double)])?.self) { group in
            for ticker in allTickers {
                group.addTask {
                    guard let prices = try? await self.fetchHistoricalPrices(ticker: ticker, start: startDate, end: endDate) else { return nil }
                    return (ticker, prices)
                }
            }
            for await result in group {
                if let (ticker, prices) = result {
                    historicalPrices[ticker] = prices
                }
            }
        }

        // Build aligned date index — normalize all timestamps to midnight to avoid
        // floating-point Set equality issues with near-equal timestamps (Bug 14)
        let calendar = Calendar.current
        let allDates = historicalPrices.values.flatMap { $0.map(\.date) }
        guard !allDates.isEmpty else { throw BacktestError.noData }
        let normalizedDates = allDates.map { calendar.startOfDay(for: $0) }
        let uniqueSortedDates = Array(Set(normalizedDates)).sorted()

        // Rebuild historicalPrices with normalized dates so lookups work correctly
        var normalizedPrices: [String: [(date: Date, close: Double)]] = [:]
        for (ticker, entries) in historicalPrices {
            normalizedPrices[ticker] = entries.map { (calendar.startOfDay(for: $0.date), $0.close) }
        }

        let fmt = DateFormatter(); fmt.dateFormat = "yyyy-MM-dd"

        // Portfolio values
        var portfolioValues: [Double] = []
        for d in uniqueSortedDates {
            var total = 0.0
            for (asset, ticker) in backTestAssets {
                let qty = asset.quantity
                if let prices = normalizedPrices[ticker],
                   let entry = prices.last(where: { $0.date <= d }) {
                    total += qty * entry.close
                }
            }
            portfolioValues.append(total)
        }

        // Trim leading zero values before assets have data (Bug 5)
        let firstNonZero = portfolioValues.firstIndex(where: { $0 > 0 }) ?? 0
        let trimmedDates = Array(uniqueSortedDates[firstNonZero...])
        let trimmedPortfolioValues = Array(portfolioValues[firstNonZero...])

        // Benchmark values — align to trimmedDates[0] for correct scale (Bug 6)
        var benchmarkValues: [Double?]? = nil
        if let bm = benchmark, let bmPrices = normalizedPrices[bm] {
            let firstValidPV = trimmedPortfolioValues.first(where: { $0 > 0 }) ?? 1.0
            let alignDate = trimmedDates.first ?? uniqueSortedDates.first ?? Date()
            let firstBM = bmPrices.last(where: { $0.date <= alignDate })?.close ?? bmPrices.first?.close ?? 1.0
            let scale = firstBM > 0 ? firstValidPV / firstBM : 1.0
            benchmarkValues = trimmedDates.map { d in
                bmPrices.last(where: { $0.date <= d }).map { $0.close * scale }
            }
        }

        // Metrics
        let validPV = trimmedPortfolioValues.filter { $0 > 0 }
        var totalReturn = 0.0, cagr = 0.0, maxDD = 0.0
        if validPV.count >= 2 {
            totalReturn = (validPV.last! - validPV.first!) / validPV.first!
            let years = endDate.timeIntervalSince(startDate) / (365.25 * 86400)
            cagr = years > 0 ? pow(validPV.last! / validPV.first!, 1.0 / years) - 1.0 : 0.0
            maxDD = calcMaxDrawdown(validPV)
        }

        // Per-asset returns
        var assetReturns: [(name: String, ticker: String, returnPct: Double)] = []
        for (asset, ticker) in backTestAssets {
            if let prices = normalizedPrices[ticker], prices.count >= 2 {
                let ret = (prices.last!.close - prices.first!.close) / prices.first!.close
                assetReturns.append((asset.name, ticker, ret))
            }
        }
        assetReturns.sort { $0.returnPct > $1.returnPct }

        return BacktestResult(
            dates: trimmedDates.map { fmt.string(from: $0) },
            portfolioValues: trimmedPortfolioValues,
            benchmarkValues: benchmarkValues,
            totalReturn: totalReturn,
            cagr: cagr,
            maxDrawdown: maxDD,
            assetReturns: assetReturns,
            skipped: skipped,
            benchmark: benchmark
        )
    }

    private func yahooTicker(for asset: Asset) -> String? {
        guard let ticker = asset.ticker, !ticker.isEmpty else { return nil }
        switch asset.category {
        case .crypto:
            let upper = ticker.uppercased()
            if upper.hasSuffix("-USD") || upper.hasSuffix("-USDT") { return upper }
            return cryptoTickerMap[ticker.lowercased()] ?? "\(upper)-USD"
        case .stock, .stockTW, .etf, .commodity:
            return ticker
        default:
            return nil
        }
    }

    private func calcMaxDrawdown(_ values: [Double]) -> Double {
        var peak = values[0], maxDD = 0.0
        for v in values {
            if v > peak { peak = v }
            if peak > 0 { maxDD = max(maxDD, (peak - v) / peak) }
        }
        return maxDD
    }

    func fetchHistoricalPrices(ticker: String, start: Date, end: Date) async throws -> [(date: Date, close: Double)] {
        let startTs = Int(start.timeIntervalSince1970)
        let endTs = Int(end.timeIntervalSince1970)
        let urlStr = "https://query1.finance.yahoo.com/v8/finance/chart/\(ticker)?interval=1d&period1=\(startTs)&period2=\(endTs)"
        guard let url = URL(string: urlStr) else { throw BacktestError.invalidURL }

        var req = URLRequest(url: url, timeoutInterval: 20)
        req.setValue("Mozilla/5.0", forHTTPHeaderField: "User-Agent")
        let (data, _) = try await URLSession.shared.data(for: req)

        struct ChartResponse: Decodable {
            struct Chart: Decodable {
                struct Result: Decodable {
                    let timestamp: [Int]?
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

        let resp = try JSONDecoder().decode(ChartResponse.self, from: data)
        guard let result = resp.chart.result?.first,
              let timestamps = result.timestamp,
              let closes = result.indicators.quote.first?.close else {
            return []
        }

        return zip(timestamps, closes).compactMap { (ts, close) in
            guard let c = close else { return nil }
            return (Date(timeIntervalSince1970: Double(ts)), c)
        }
    }
}

enum BacktestError: LocalizedError {
    case noTickers
    case noData
    case invalidURL

    var errorDescription: String? {
        switch self {
        case .noTickers: return "沒有可回測的資產（需要有代碼的股票、ETF 或加密貨幣）"
        case .noData: return "無法取得歷史資料，請確認日期範圍"
        case .invalidURL: return "無效的 URL"
        }
    }
}
