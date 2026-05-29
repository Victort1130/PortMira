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

    // Effective bounds: use per-asset min/max if set, otherwise fall back to target ± tolerance
    var effectiveLo: Double { asset.targetMinPct ?? (targetPct - tolerance) }
    var effectiveHi: Double { asset.targetMaxPct ?? (targetPct + tolerance) }

    var action: String {
        if currentPct < effectiveLo { return "買入 Buy" }
        if currentPct > effectiveHi { return "賣出 Sell" }
        return "持有 Hold"
    }

    var targetRange: String {
        String(format: "%.0f%% – %.0f%%", max(0, effectiveLo), effectiveHi)
    }
}

struct ScenarioResult {
    var enrichedAssets:   [EnrichedAsset]
    var totalAssets:      Double
    var totalLiabilities: Double
    var netWorth:         Double
}
