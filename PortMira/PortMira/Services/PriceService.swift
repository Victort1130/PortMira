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

    // MARK: - CoinGecko (crypto)

    static func fetchCryptoPrices(ids: [String]) async -> [String: Double] {
        guard !ids.isEmpty,
              let url = URL(string: "https://api.coingecko.com/api/v3/simple/price?ids=\(ids.joined(separator: ","))&vs_currencies=usd&include_24hr_change=true")
        else { return [:] }
        do {
            let (data, response) = try await URLSession.shared.data(from: url)
            if let http = response as? HTTPURLResponse, http.statusCode == 429 {
                print("[PriceService] CoinGecko rate limit")
                return [:]
            }
            let json = try JSONDecoder().decode([String: [String: Double]].self, from: data)
            var prices: [String: Double] = [:]
            for id in ids {
                if let p = json[id]?["usd"] { prices[id] = p }
            }
            return prices
        } catch {
            print("[PriceService] CoinGecko: \(error)")
            return [:]
        }
    }

    static func fetchCryptoPrevCloses(ids: [String]) async -> [String: Double] {
        guard !ids.isEmpty,
              let url = URL(string: "https://api.coingecko.com/api/v3/simple/price?ids=\(ids.joined(separator: ","))&vs_currencies=usd&include_24hr_change=true")
        else { return [:] }
        do {
            let (data, _) = try await URLSession.shared.data(from: url)
            let json = try JSONDecoder().decode([String: [String: Double]].self, from: data)
            var prevCloses: [String: Double] = [:]
            for id in ids {
                guard let price = json[id]?["usd"],
                      let change = json[id]?["usd_24h_change"],
                      price > 0
                else { continue }
                let divisor = 1 + change / 100
                if divisor != 0 { prevCloses[id] = price / divisor }
            }
            return prevCloses
        } catch {
            return [:]
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
        // Includes stock, stock_tw, etf, commodity (all have isAutoPrice == true and are not .crypto)
        let stockTickers = assets.filter { $0.category.isAutoPrice && $0.category != .crypto }
                                  .compactMap { $0.ticker }
        let cryptoIds    = assets.filter { $0.category == .crypto }.compactMap { $0.ticker }

        async let stockPrices     = fetchStockPrices(tickers: stockTickers)
        async let stockPrevCloses = fetchPrevCloses(tickers: stockTickers)
        async let cryptoPrices    = fetchCryptoPrices(ids: cryptoIds)
        async let cryptoPrevClose = fetchCryptoPrevCloses(ids: cryptoIds)

        let (sp, spc, cp, cpc) = await (stockPrices, stockPrevCloses, cryptoPrices, cryptoPrevClose)
        return (sp.merging(cp) { a, _ in a }, spc.merging(cpc) { a, _ in a })
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
