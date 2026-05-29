import Foundation

struct EnrichedAsset: Identifiable {
    var id:             String
    var asset:          Asset
    var currentPrice:   Double
    var fxRate:         Double
    var marketValue:    Double
    var costBasis:      Double
    var unrealizedPL:   Double
    var unrealizedPLPct: Double?
    var dailyChangePct: Double?
    var cagr:           Double?

    var name:     String        { asset.name }
    var ticker:   String?       { asset.ticker }
    var category: AssetCategory { asset.category }
    var currency: Currency      { asset.currency }
    var quantity: Double        { asset.quantity }
}

struct RebalanceAction: Identifiable {
    var id:          String { asset.id }
    var asset:       Asset
    var currentPct:  Double
    var targetPct:   Double
    var tolerance:   Double  // percentage points, e.g. 5.0
    var deltaValue:  Double
    var deltaUnits:  Double?

    var action: String {
        let diff = currentPct - targetPct
        if diff < -tolerance { return "買入 Buy" }
        if diff > tolerance  { return "賣出 Sell" }
        return "持有 Hold"
    }

    var targetRange: String {
        let lo = max(0, targetPct - tolerance)
        let hi = targetPct + tolerance
        return String(format: "%.0f%% – %.0f%%", lo, hi)
    }
}

struct ScenarioResult {
    var enrichedAssets:   [EnrichedAsset]
    var totalAssets:      Double
    var totalLiabilities: Double
    var netWorth:         Double
}
