import SwiftUI
import Charts

// MARK: - Stats Card

struct StatsCard: View {
    let title:    String
    let value:    String
    var subtitle: String?  = nil
    var color:    Color    = .primary

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title)
                .font(.caption)
                .foregroundStyle(.secondary)
            Text(value)
                .font(.title3).fontWeight(.semibold)
                .foregroundStyle(color)
                .lineLimit(1)
                .minimumScaleFactor(0.7)
            if let sub = subtitle {
                Text(sub)
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .background(.quaternary, in: RoundedRectangle(cornerRadius: 10))
    }
}

// MARK: - Portfolio Stats View

struct PortfolioStatsView: View {
    @Environment(PortfolioStore.self) private var store

    @State private var spyReturns:    [Double] = []
    @State private var isFetchingSPY: Bool     = false
    @State private var spyError:      String?  = nil

    // MARK: Computed stats

    private var enriched: [EnrichedAsset] { store.enrichedAssets }
    private var liabilities: [Liability]  { store.portfolio.liabilities }
    private var fxRates: [String: Double] { store.fxRates }

    // 1. Margin Ratio (融資維持率)
    private var marginRatioResult: (value: Double?, hasMargin: Bool) {
        let totalMV    = enriched.reduce(0) { $0 + $1.marketValue }
        let marginLoans = liabilities.filter { $0.category == .marginLoan }
        guard !marginLoans.isEmpty else { return (nil, false) }
        let totalLoan  = marginLoans.reduce(0) { $0 + $1.amount * (fxRates[$1.currency.rawValue] ?? 1.0) }
        guard totalLoan > 0 else { return (nil, false) }
        return (totalMV / totalLoan * 100, true)
    }

    private var marginRatioColor: Color {
        guard let r = marginRatioResult.value else { return .secondary }
        if r >= 166 { return .green }
        if r >= 130 { return .orange }
        return .red
    }

    private var marginRatioText: String {
        if !marginRatioResult.hasMargin { return "無融資" }
        guard let r = marginRatioResult.value else { return "—" }
        return String(format: "%.1f%%", r)
    }

    // 2. Monthly Interest (月利息)
    private var monthlyInterest: Double {
        CalculationsEngine.calcMonthlyInterest(liabilities: liabilities, fxRates: fxRates)
    }

    private var baseCurrency: String { store.baseCurrency }

    // 3. Sharpe Ratio
    private var sharpeResult: String {
        let dailyReturns = portfolioReturns
        guard dailyReturns.count >= 20 else { return "資料不足" }
        let mean = dailyReturns.reduce(0, +) / Double(dailyReturns.count)
        let variance = dailyReturns.map { pow($0 - mean, 2) }.reduce(0, +) / Double(dailyReturns.count)
        let dailyVol = sqrt(variance)
        guard dailyVol > 0 else { return "—" }
        let annReturn = mean * 252
        let annVol    = dailyVol * sqrt(252)
        let sharpe    = annReturn / annVol
        return String(format: "%.2f", sharpe)
    }

    // 4. Portfolio Beta
    private var betaResult: String {
        guard !isFetchingSPY else { return "計算中" }
        if let _ = spyError { return "無法取得" }
        guard spyReturns.count >= 20 else { return spyReturns.isEmpty ? "計算中" : "資料不足" }
        let portReturns = portfolioReturns
        guard portReturns.count >= 20 else { return "資料不足" }

        // Align lengths
        let len = min(portReturns.count, spyReturns.count)
        let port = Array(portReturns.suffix(len))
        let spy  = Array(spyReturns.suffix(len))

        let portMean = port.reduce(0, +) / Double(len)
        let spyMean  = spy.reduce(0, +)  / Double(len)

        var cov = 0.0, varSPY = 0.0
        for i in 0..<len {
            cov    += (port[i] - portMean) * (spy[i] - spyMean)
            varSPY += pow(spy[i] - spyMean, 2)
        }
        guard varSPY > 0 else { return "—" }
        let beta = cov / varSPY
        return String(format: "%.2f", beta)
    }

    // 5. Weighted Average Cost
    private var weightedAvgCostText: String {
        let totalMV = enriched.reduce(0) { $0 + $1.marketValue }
        let totalCB = enriched.reduce(0) { $0 + $1.costBasis }
        guard totalCB > 0, totalMV > 0 else { return "—" }
        let ratio = totalMV / totalCB
        return String(format: "%.3f×", ratio)
    }

    private var weightedAvgCostColor: Color {
        let totalMV = enriched.reduce(0) { $0 + $1.marketValue }
        let totalCB = enriched.reduce(0) { $0 + $1.costBasis }
        guard totalCB > 0 else { return .primary }
        return totalMV >= totalCB ? .green : .red
    }

    // 6. Total Unrealized P&L
    private var totalUnrealizedPL: Double {
        enriched.reduce(0) { $0 + $1.unrealizedPL }
    }

    // Portfolio daily-return time series (market-value weighted), fetched from
    // ~200 days of price history so Sharpe/Beta have a real series instead of a
    // single live-price data point (which always read "資料不足").
    @State private var portfolioReturns: [Double] = []

    private func fetchPortfolioReturns() async {
        let totalMV = enriched.reduce(0) { $0 + $1.marketValue }
        guard totalMV > 0 else { return }
        let svc = CandlestickService()
        var series: [(weight: Double, returns: [Double])] = []
        for ea in enriched {
            guard let ticker = ea.asset.ticker, !ticker.isEmpty,
                  ea.category != .cash, ea.category != .other else { continue }
            let yf = ea.category == .crypto ? cryptoToYahooTicker(ticker) : ticker
            guard let bars = try? await svc.fetchOHLCV(ticker: yf), bars.count > 1 else { continue }
            let closes = bars.map(\.close)
            let rets = zip(closes.dropFirst(), closes.dropLast()).map { ($0 - $1) / $1 }
            if !rets.isEmpty { series.append((ea.marketValue / totalMV, rets)) }
        }
        guard let minLen = series.map({ $0.returns.count }).min(), minLen >= 20 else {
            portfolioReturns = []
            return
        }
        // Cash / untracked assets keep their weight (zero return) so they
        // correctly dilute the portfolio's volatility.
        var combined = [Double](repeating: 0, count: minLen)
        for entry in series {
            let tail = Array(entry.returns.suffix(minLen))
            for i in 0..<minLen { combined[i] += tail[i] * entry.weight }
        }
        portfolioReturns = combined
    }

    private func cryptoToYahooTicker(_ id: String) -> String {
        let upper = id.uppercased()
        if upper.hasSuffix("-USD") || upper.hasSuffix("-USDT") { return upper }
        let map: [String: String] = [
            "bitcoin": "BTC-USD", "ethereum": "ETH-USD", "binancecoin": "BNB-USD",
            "cardano": "ADA-USD", "solana": "SOL-USD", "ripple": "XRP-USD",
            "dogecoin": "DOGE-USD",
        ]
        return map[id.lowercased()] ?? "\(upper)-USD"
    }

    // MARK: Body

    var body: some View {
        let columns = [GridItem(.flexible()), GridItem(.flexible())]

        LazyVGrid(columns: columns, spacing: 12) {
            // 1. Margin Ratio
            StatsCard(
                title:    "融資維持率",
                value:    marginRatioText,
                subtitle: marginRatioResult.hasMargin ? "≥ 166% 安全" : nil,
                color:    marginRatioResult.hasMargin ? marginRatioColor : .secondary
            )

            // 2. Monthly Interest
            StatsCard(
                title:    "月利息",
                value:    monthlyInterest == 0
                              ? "無負債利息"
                              : monthlyInterest.formatted(.number.precision(.fractionLength(0))) + " \(baseCurrency)",
                subtitle: "所有負債合計",
                color:    monthlyInterest > 0 ? .orange : .secondary
            )

            // 3. Sharpe Ratio
            StatsCard(
                title:    "夏普比率",
                value:    sharpeResult,
                subtitle: "年化報酬 / 年化波動",
                color:    sharpeColor
            )

            // 4. Portfolio Beta
            StatsCard(
                title:    "Portfolio β",
                value:    betaResult,
                subtitle: "vs SPY（3 個月）",
                color:    .primary
            )

            // 5. Weighted Average Cost
            StatsCard(
                title:    "加權平均成本比",
                value:    weightedAvgCostText,
                subtitle: "市值 / 成本",
                color:    weightedAvgCostColor
            )

            // 6. Unrealized P&L
            StatsCard(
                title:    "未實現損益",
                value:    totalUnrealizedPL.formatted(.number.precision(.fractionLength(0))) + " \(baseCurrency)",
                subtitle: "所有資產合計",
                color:    totalUnrealizedPL >= 0 ? .green : .red
            )
        }
        .padding(.horizontal)
        .task {
            await fetchSPY()
            await fetchPortfolioReturns()
        }
    }

    // MARK: - Helpers

    private var sharpeColor: Color {
        guard let v = Double(sharpeResult) else { return .secondary }
        if v >= 1.0  { return .green }
        if v >= 0.0  { return .primary }
        return .red
    }

    private func fetchSPY() async {
        isFetchingSPY = true
        spyError      = nil
        defer { isFetchingSPY = false }
        do {
            let svc = CandlestickService()
            let bars = try await svc.fetchOHLCV(ticker: "SPY")
            let closes = bars.map(\.close)
            spyReturns = zip(closes.dropFirst(), closes.dropLast()).map { ($0 - $1) / $1 }
        } catch {
            spyError   = error.localizedDescription
            spyReturns = []
        }
    }
}
