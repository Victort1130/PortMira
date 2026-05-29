import Foundation

enum CalculationsEngine {

    // MARK: - Enrich assets with live prices

    static func enrich(
        assets:       [Asset],
        prices:       [String: Double],
        prevCloses:   [String: Double],
        fxRates:      [String: Double],
        baseCurrency: String
    ) -> [EnrichedAsset] {
        assets.map { asset in
            let currentPrice: Double = {
                if asset.category == .cash { return 1.0 }
                if let ticker = asset.ticker, let p = prices[ticker] { return p }
                return asset.costPerUnit
            }()

            let fxRate     = fxRates[asset.currency.rawValue] ?? 1.0
            let marketValue = asset.quantity * currentPrice * fxRate
            let costBasis   = asset.quantity * asset.costPerUnit * fxRate
            let pl          = marketValue - costBasis
            let plPct       = costBasis > 0 ? pl / costBasis : nil

            let dailyChangePct: Double? = {
                guard let ticker = asset.ticker,
                      let prev = prevCloses[ticker], prev > 0
                else { return nil }
                return (currentPrice - prev) / prev
            }()

            let cagr = calcAssetCagr(
                marketValue:      marketValue,
                costBasis:        costBasis,
                purchaseDateStr:  asset.purchaseDate
            )

            return EnrichedAsset(
                id:              asset.id,
                asset:           asset,
                currentPrice:    currentPrice,
                fxRate:          fxRate,
                marketValue:     marketValue,
                costBasis:       costBasis,
                unrealizedPL:    pl,
                unrealizedPLPct: plPct,
                dailyChangePct:  dailyChangePct,
                cagr:            cagr
            )
        }
    }

    // MARK: - Net worth

    static func netWorth(
        enrichedAssets: [EnrichedAsset],
        liabilities:    [Liability],
        fxRates:        [String: Double]
    ) -> (assets: Double, liabilities: Double, net: Double) {
        let totalAssets = enrichedAssets.reduce(0) { $0 + $1.marketValue }
        let totalLiab   = liabilities.reduce(0) {
            $0 + $1.amount * (fxRates[$1.currency.rawValue] ?? 1.0)
        }
        return (totalAssets, totalLiab, totalAssets - totalLiab)
    }

    // MARK: - Portfolio CAGR

    static func portfolioCagr(enrichedAssets: [EnrichedAsset]) -> Double? {
        let withDates = enrichedAssets.filter { $0.asset.purchaseDate != nil }
        guard !withDates.isEmpty else { return nil }

        let formatter = DateFormatter.yyyyMMdd
        guard let earliest = withDates.compactMap({ $0.asset.purchaseDate })
                                       .compactMap({ formatter.date(from: $0) })
                                       .min()
        else { return nil }

        let years = Date().timeIntervalSince(earliest) / 31_557_600
        guard years > 0.01 else { return nil }

        let totalMV = withDates.reduce(0) { $0 + $1.marketValue }
        let totalCB = withDates.reduce(0) { $0 + $1.costBasis }
        guard totalCB > 0, totalMV > 0 else { return nil }

        return pow(totalMV / totalCB, 1.0 / years) - 1.0
    }

    // MARK: - Per-asset CAGR

    static func calcAssetCagr(
        marketValue:     Double,
        costBasis:       Double,
        purchaseDateStr: String?
    ) -> Double? {
        guard let dateStr = purchaseDateStr,
              let purchase = DateFormatter.yyyyMMdd.date(from: dateStr),
              costBasis > 0, marketValue > 0
        else { return nil }

        let years = Date().timeIntervalSince(purchase) / 31_557_600
        guard years > 0.01 else { return nil }
        return pow(marketValue / costBasis, 1.0 / years) - 1.0
    }

    // MARK: - Rebalancing

    static func calcRebalance(enrichedAssets: [EnrichedAsset], tolerance: Double = 5.0) -> [RebalanceAction] {
        let withTargets = enrichedAssets.filter {
            if let t = $0.asset.targetPct { return t > 0 } else { return false }
        }
        guard !withTargets.isEmpty else { return [] }

        let totalValue = enrichedAssets.reduce(0) { $0 + $1.marketValue }
        guard totalValue > 0 else { return [] }

        return withTargets.map { ea in
            let targetPct   = ea.asset.targetPct!
            let currentPct  = ea.marketValue / totalValue * 100
            let targetValue = totalValue * targetPct / 100
            let delta       = targetValue - ea.marketValue

            let priceInBase = ea.currentPrice * ea.fxRate
            let deltaUnits  = priceInBase > 0 ? delta / priceInBase : nil

            return RebalanceAction(
                asset:      ea.asset,
                currentPct: currentPct,
                targetPct:  targetPct,
                tolerance:  tolerance,
                deltaValue: delta,
                deltaUnits: deltaUnits
            )
        }
        .sorted { abs($0.deltaValue) > abs($1.deltaValue) }
    }

    // MARK: - Scenario analysis

    static func applyScenario(
        enrichedAssets:  [EnrichedAsset],
        liabilities:     [Liability],
        fxRates:         [String: Double],
        categoryShocks:  [String: Double],
        fxShocks:        [String: Double]
    ) -> ScenarioResult {
        let newFxByCurrency: [String: Double] = Dictionary(
            uniqueKeysWithValues: fxRates.keys.map { ccy in
                (ccy, fxRates[ccy]! * (1 + (fxShocks[ccy] ?? 0)))
            }
        )

        let scenarioAssets = enrichedAssets.map { ea -> EnrichedAsset in
            let shock        = categoryShocks[ea.category.rawValue] ?? 0
            let newPrice     = ea.currentPrice * (1 + shock)
            let newFxRate    = newFxByCurrency[ea.currency.rawValue] ?? ea.fxRate
            let newMV        = ea.quantity * newPrice * newFxRate
            let newPL        = newMV - ea.costBasis
            let newPLPct     = ea.costBasis > 0 ? newPL / ea.costBasis : nil

            var updated          = ea
            updated.currentPrice = newPrice
            updated.fxRate       = newFxRate
            updated.marketValue  = newMV
            updated.unrealizedPL = newPL
            updated.unrealizedPLPct = newPLPct
            return updated
        }

        let totalAssets = scenarioAssets.reduce(0) { $0 + $1.marketValue }
        let totalLiab   = liabilities.reduce(0) {
            $0 + $1.amount * (newFxByCurrency[$1.currency.rawValue] ?? 1.0)
        }

        return ScenarioResult(
            enrichedAssets:   scenarioAssets,
            totalAssets:      totalAssets,
            totalLiabilities: totalLiab,
            netWorth:         totalAssets - totalLiab
        )
    }
}
