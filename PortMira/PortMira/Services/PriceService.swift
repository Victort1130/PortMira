import Foundation

enum PriceService {

    // MARK: - Yahoo Finance (stocks / ETFs)

    static func fetchStockPrices(tickers: [String]) async -> [String: Double] {
        await withTaskGroup(of: (String, Double?).self) { group in
            for ticker in tickers {
                group.addTask { (ticker, await fetchYahooPrice(ticker: ticker)) }
            }
            var result: [String: Double] = [:]
            for await (ticker, price) in group {
                if let price { result[ticker] = price }
            }
            return result
        }
    }

    static func fetchPrevCloses(tickers: [String]) async -> [String: Double] {
        await withTaskGroup(of: (String, Double?).self) { group in
            for ticker in tickers {
                group.addTask { (ticker, await fetchYahooPrevClose(ticker: ticker)) }
            }
            var result: [String: Double] = [:]
            for await (ticker, price) in group {
                if let price { result[ticker] = price }
            }
            return result
        }
    }

    private static func fetchYahooPrice(ticker: String) async -> Double? {
        guard let url = URL(string: "https://query2.finance.yahoo.com/v8/finance/chart/\(ticker)?interval=1d&range=1d") else { return nil }
        do {
            let (data, _) = try await URLSession.shared.data(from: url)
            let resp = try JSONDecoder().decode(YahooChartResponse.self, from: data)
            return resp.chart.result?.first?.meta.regularMarketPrice
        } catch {
            print("[PriceService] Yahoo \(ticker): \(error)")
            return nil
        }
    }

    private static func fetchYahooPrevClose(ticker: String) async -> Double? {
        guard let url = URL(string: "https://query2.finance.yahoo.com/v8/finance/chart/\(ticker)?interval=1d&range=1d") else { return nil }
        do {
            let (data, _) = try await URLSession.shared.data(from: url)
            let resp = try JSONDecoder().decode(YahooChartResponse.self, from: data)
            return resp.chart.result?.first?.meta.chartPreviousClose
                ?? resp.chart.result?.first?.meta.previousClose
        } catch {
            return nil
        }
    }

    // MARK: - FX Rates

    static func fetchFXRates(currencies: [String], base: String) async -> [String: Double] {
        var result: [String: Double] = [base: 1.0]
        let foreign = currencies.filter { $0 != base }
        guard !foreign.isEmpty,
              let url = URL(string: "https://api.exchangerate-api.com/v4/latest/\(base)")
        else { return result }
        do {
            let (data, _) = try await URLSession.shared.data(from: url)
            let resp = try JSONDecoder().decode(ExchangeRateResponse.self, from: data)
            for ccy in foreign {
                if let rate = resp.rates[ccy], rate > 0 {
                    result[ccy] = 1.0 / rate
                }
            }
        } catch {
            print("[PriceService] FX: \(error)")
            for ccy in foreign { result[ccy] = 1.0 }
        }
        return result
    }

    // MARK: - Convenience: fetch all at once

    static func fetchAll(assets: [Asset]) async -> (prices: [String: Double], prevCloses: [String: Double]) {
        // All auto-priced assets (stocks, ETFs, crypto, commodity) go through Yahoo Finance.
        // Crypto tickers must be in BTC-USD format.
        let tickers = assets.filter { $0.category.isAutoPrice }.compactMap { $0.ticker }

        async let prices     = fetchStockPrices(tickers: tickers)
        async let prevCloses = fetchPrevCloses(tickers: tickers)
        return await (prices, prevCloses)
    }
}

// MARK: - Response models

private struct YahooChartResponse: Decodable {
    struct Chart: Decodable {
        struct Result: Decodable {
            struct Meta: Decodable {
                var regularMarketPrice: Double
                var previousClose:      Double?
                var chartPreviousClose: Double?
            }
            var meta: Meta
        }
        var result: [Result]?
    }
    var chart: Chart
}

private struct ExchangeRateResponse: Decodable {
    var rates: [String: Double]
}
