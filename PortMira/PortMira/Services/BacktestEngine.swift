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

private let cryptoTickerMap: [String: String] = [
    "bitcoin": "BTC-USD", "ethereum": "ETH-USD", "binancecoin": "BNB-USD",
    "cardano": "ADA-USD", "solana": "SOL-USD", "ripple": "XRP-USD",
    "polkadot": "DOT-USD", "dogecoin": "DOGE-USD", "avalanche-2": "AVAX-USD",
    "chainlink": "LINK-USD", "litecoin": "LTC-USD", "stellar": "XLM-USD"
]

actor BacktestEngine {
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

        // Build aligned date index
        let allDates = historicalPrices.values.flatMap { $0.map(\.date) }
        guard !allDates.isEmpty else { throw BacktestError.noData }
        let uniqueSortedDates = Array(Set(allDates)).sorted()

        let fmt = DateFormatter(); fmt.dateFormat = "yyyy-MM-dd"

        // Portfolio values
        var portfolioValues: [Double] = []
        for d in uniqueSortedDates {
            var total = 0.0
            for (asset, ticker) in backTestAssets {
                let qty = asset.quantity
                if let prices = historicalPrices[ticker],
                   let entry = prices.last(where: { $0.date <= d }) {
                    total += qty * entry.close
                }
            }
            portfolioValues.append(total)
        }

        // Benchmark values
        var benchmarkValues: [Double?]? = nil
        if let bm = benchmark, let bmPrices = historicalPrices[bm] {
            let firstValidPV = portfolioValues.first(where: { $0 > 0 }) ?? 1.0
            let firstBM = bmPrices.first?.close ?? 1.0
            let scale = firstBM > 0 ? firstValidPV / firstBM : 1.0
            benchmarkValues = uniqueSortedDates.map { d in
                bmPrices.last(where: { $0.date <= d }).map { $0.close * scale }
            }
        }

        // Metrics
        let validPV = portfolioValues.filter { $0 > 0 }
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
            if let prices = historicalPrices[ticker], prices.count >= 2 {
                let ret = (prices.last!.close - prices.first!.close) / prices.first!.close
                assetReturns.append((asset.name, ticker, ret))
            }
        }
        assetReturns.sort { $0.returnPct > $1.returnPct }

        return BacktestResult(
            dates: uniqueSortedDates.map { fmt.string(from: $0) },
            portfolioValues: portfolioValues,
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
            return cryptoTickerMap[ticker.lowercased()] ?? "\(ticker.uppercased())-USD"
        case .stock, .stockTW, .etf:
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
