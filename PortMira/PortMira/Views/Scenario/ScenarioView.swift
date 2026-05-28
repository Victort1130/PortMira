import SwiftUI

struct ScenarioView: View {
    @Environment(PortfolioStore.self) private var store

    @State private var shockStock:     Double = 0
    @State private var shockStockTW:   Double = 0
    @State private var shockETF:       Double = 0
    @State private var shockCrypto:    Double = 0
    @State private var shockCommodity: Double = 0
    @State private var shockOther:     Double = 0

    @State private var fxUSD: Double = 0
    @State private var fxEUR: Double = 0
    @State private var fxJPY: Double = 0

    @State private var scenarioName:     String    = ""
    @State private var selectedScenario: Scenario? = nil

    @State private var selectedEventId: String? = nil

    var categoryShocks: [String: Double] {[
        "stock":     shockStock / 100,
        "stock_tw":  shockStockTW / 100,
        "etf":       shockETF / 100,
        "crypto":    shockCrypto / 100,
        "commodity": shockCommodity / 100,
        "other":     shockOther / 100,
    ]}

    var fxShocks: [String: Double] {[
        "USD": fxUSD / 100, "EUR": fxEUR / 100, "JPY": fxJPY / 100,
    ]}

    var result: ScenarioResult? {
        guard !store.enrichedAssets.isEmpty else { return nil }
        return CalculationsEngine.applyScenario(
            enrichedAssets:  store.enrichedAssets,
            liabilities:     store.portfolio.liabilities,
            fxRates:         store.fxRates,
            categoryShocks:  categoryShocks,
            fxShocks:        fxShocks
        )
    }

    var body: some View {
        HSplitView {
            controlsPanel
            resultsPanel
        }
        .navigationTitle("情境分析")
    }

    // MARK: - Left panel

    private var controlsPanel: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {

                // Historical event presets
                VStack(alignment: .leading, spacing: 8) {
                    Text("歷史重大事件 Presets").font(.headline)
                    Picker("歷史重大事件", selection: $selectedEventId) {
                        Text("自訂").tag(Optional<String>.none)
                        ForEach(historicalEvents) { event in
                            Text(event.name).tag(Optional(event.id))
                        }
                    }
                    .onChange(of: selectedEventId) { _, eventId in
                        applyHistoricalEvent(id: eventId)
                    }

                    if let eventId = selectedEventId,
                       let event = historicalEvents.first(where: { $0.id == eventId }) {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(event.period)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                            Text(event.description)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                        .padding(.top, 2)

                        DisclosureGroup("💡 避險建議") {
                            VStack(alignment: .leading, spacing: 4) {
                                ForEach(event.hedgingTips, id: \.self) { tip in
                                    HStack(alignment: .top, spacing: 4) {
                                        Text("•")
                                        Text(tip)
                                            .font(.caption)
                                            .fixedSize(horizontal: false, vertical: true)
                                    }
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                                }
                            }
                            .padding(.top, 4)
                        }
                        .font(.subheadline)
                    }
                }

                Divider()

                if !store.portfolio.scenarios.isEmpty {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("已儲存情境").font(.headline)
                        Picker("情境", selection: $selectedScenario) {
                            Text("（新情境）").tag(Optional<Scenario>.none)
                            ForEach(store.portfolio.scenarios) { sc in
                                Text(sc.name).tag(Optional(sc))
                            }
                        }
                        .onChange(of: selectedScenario) { _, sc in loadScenario(sc) }
                    }
                    Divider()
                }

                VStack(alignment: .leading, spacing: 12) {
                    Text("資產類別漲跌幅").font(.headline)
                    ShockSlider(label: "股票 Stock",           value: $shockStock)
                    ShockSlider(label: "台股 TW Stock",        value: $shockStockTW)
                    ShockSlider(label: "ETF",                  value: $shockETF)
                    ShockSlider(label: "加密貨幣 Crypto",      value: $shockCrypto)
                    ShockSlider(label: "大宗商品 Commodity",   value: $shockCommodity)
                    ShockSlider(label: "其他 Other",           value: $shockOther)
                }

                Divider()

                VStack(alignment: .leading, spacing: 12) {
                    Text("匯率變動").font(.headline)
                    Text("正 = 外幣升值（持有外幣資產市值上升）")
                        .font(.caption).foregroundStyle(.secondary)
                    ShockSlider(label: "USD", value: $fxUSD, range: -30...30)
                    ShockSlider(label: "EUR", value: $fxEUR, range: -30...30)
                    ShockSlider(label: "JPY", value: $fxJPY, range: -30...30)
                }

                Divider()

                VStack(alignment: .leading, spacing: 8) {
                    Text("儲存情境").font(.headline)
                    TextField("情境名稱", text: $scenarioName)
                        .textFieldStyle(.roundedBorder)
                    HStack {
                        Button("儲存") { saveCurrentScenario() }
                            .buttonStyle(.borderedProminent)
                            .disabled(scenarioName.trimmingCharacters(in: .whitespaces).isEmpty)
                        if selectedScenario != nil {
                            Button("刪除", role: .destructive) {
                                if let sc = selectedScenario {
                                    store.deleteScenario(sc)
                                    selectedScenario = nil
                                    scenarioName = ""
                                }
                            }
                            .buttonStyle(.bordered)
                        }
                    }
                }
            }
            .padding()
        }
        .frame(minWidth: 280, maxWidth: 320)
    }

    // MARK: - Right panel

    private var resultsPanel: some View {
        ScrollView {
            if store.enrichedAssets.isEmpty {
                ContentUnavailableView(
                    "尚無持倉資料",
                    systemImage: "wand.and.stars",
                    description: Text("請先新增資產並 Refresh 價格。")
                )
            } else if let r = result {
                ScenarioResultView(result: r, baseline: store.enrichedAssets,
                                   baseNetWorth: store.netWorth,
                                   baseTotalAssets: store.totalAssets,
                                   currency: store.baseCurrency)
            }
        }
    }

    // MARK: - Helpers

    private func applyHistoricalEvent(id: String?) {
        guard let id, let event = historicalEvents.first(where: { $0.id == id }) else { return }
        let cats = event.categoryShocks
        let fx   = event.fxShocks
        shockStock     = (cats["stock"]     ?? 0) * 100
        shockStockTW   = (cats["stock_tw"]  ?? 0) * 100
        shockETF       = (cats["etf"]       ?? 0) * 100
        shockCrypto    = (cats["crypto"]    ?? 0) * 100
        shockCommodity = (cats["commodity"] ?? 0) * 100
        shockOther     = (cats["other"]     ?? 0) * 100
        fxUSD = (fx["USD"] ?? 0) * 100
        fxEUR = (fx["EUR"] ?? 0) * 100
        fxJPY = (fx["JPY"] ?? 0) * 100
    }

    private func loadScenario(_ sc: Scenario?) {
        guard let sc else { return }
        selectedEventId = nil
        scenarioName = sc.name
        let cats = sc.shocks.categories
        let fx   = sc.shocks.fx
        shockStock     = (cats["stock"]     ?? 0) * 100
        shockStockTW   = (cats["stock_tw"]  ?? 0) * 100
        shockETF       = (cats["etf"]       ?? 0) * 100
        shockCrypto    = (cats["crypto"]    ?? 0) * 100
        shockCommodity = (cats["commodity"] ?? 0) * 100
        shockOther     = (cats["other"]     ?? 0) * 100
        fxUSD = (fx["USD"] ?? 0) * 100
        fxEUR = (fx["EUR"] ?? 0) * 100
        fxJPY = (fx["JPY"] ?? 0) * 100
    }

    private func saveCurrentScenario() {
        let name = scenarioName.trimmingCharacters(in: .whitespaces)
        guard !name.isEmpty else { return }
        let sc = Scenario(
            id:        selectedScenario?.id ?? "sc_\(UUID().uuidString.prefix(8))",
            name:      name,
            createdAt: DateFormatter.yyyyMMdd.string(from: Date()),
            shocks:    ScenarioShocks(categories: categoryShocks, fx: fxShocks)
        )
        store.saveScenario(sc)
        selectedScenario = sc
    }
}

// MARK: - Scenario result view (separate struct keeps the type-checker scope small)

private struct ScenarioResultView: View {
    let result:          ScenarioResult
    let baseline:        [EnrichedAsset]
    let baseNetWorth:    Double
    let baseTotalAssets: Double
    let currency:        String

    private var nwDelta:   Double { result.netWorth    - baseNetWorth }
    private var mvDelta:   Double { result.totalAssets - baseTotalAssets }
    private var pctChange: Double {
        guard baseNetWorth != 0 else { return 0 }
        return nwDelta / abs(baseNetWorth) * 100
    }

    private func nwSubtitle() -> String {
        let sign = nwDelta >= 0 ? "▲ +" : "▼ "
        return sign + nwDelta.formatted(.number.precision(.fractionLength(0)))
    }

    private func mvSubtitle() -> String {
        let sign = mvDelta >= 0 ? "▲ +" : "▼ "
        return sign + mvDelta.formatted(.number.precision(.fractionLength(0)))
    }

    private func pctValue() -> String {
        let sign = pctChange >= 0 ? "+" : ""
        return sign + pctChange.formatted(.number.precision(.fractionLength(2))) + "%"
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 24) {
            Text("模擬結果").font(.title2).fontWeight(.bold)

            LazyVGrid(
                columns: [GridItem(.flexible()), GridItem(.flexible()), GridItem(.flexible())],
                spacing: 16
            ) {
                MetricCard(
                    title:      "情境淨資產",
                    value:      result.netWorth.formatted(.number.precision(.fractionLength(0))),
                    subtitle:   nwSubtitle(),
                    valueColor: nwDelta >= 0 ? .green : .red
                )
                MetricCard(
                    title:      "情境總資產",
                    value:      result.totalAssets.formatted(.number.precision(.fractionLength(0))),
                    subtitle:   mvSubtitle(),
                    valueColor: mvDelta >= 0 ? .green : .red
                )
                MetricCard(
                    title:      "淨資產變動",
                    value:      pctValue(),
                    subtitle:   currency,
                    valueColor: pctChange >= 0 ? .green : .red
                )
            }

            Divider()

            Text("各資產情境影響").font(.headline)

            ScenarioImpactTable(scenarioAssets: result.enrichedAssets, baseline: baseline)
        }
        .padding()
    }
}

// MARK: - Impact table (isolated so the @TableColumnBuilder has a small scope)

private struct ScenarioImpactTable: View {
    let scenarioAssets: [EnrichedAsset]
    let baseline:       [EnrichedAsset]

    private func baseValue(for id: String) -> Double? {
        baseline.first(where: { $0.id == id })?.marketValue
    }

    private func impact(for ea: EnrichedAsset) -> Double {
        (baseValue(for: ea.id) ?? ea.marketValue).distance(to: ea.marketValue)
    }

    private func impactPct(for ea: EnrichedAsset) -> Double? {
        guard let base = baseValue(for: ea.id), base > 0 else { return nil }
        return (ea.marketValue - base) / base * 100
    }

    private func signedString(_ value: Double, decimals: Int) -> String {
        let formatted = value.formatted(.number.precision(.fractionLength(decimals)))
        return value >= 0 ? "+" + formatted : formatted
    }

    var body: some View {
        Table(scenarioAssets) {
            TableColumn("資產名稱") { ea in
                VStack(alignment: .leading, spacing: 2) {
                    Text(ea.name).fontWeight(.medium)
                    Text(ea.ticker ?? "—").font(.caption).foregroundStyle(.secondary)
                }
            }
            TableColumn("類別") { ea in
                Text(ea.category.displayName)
            }.width(90)
            TableColumn("現值") { ea in
                Text((baseValue(for: ea.id) ?? 0).formatted(.number.precision(.fractionLength(0))))
                    .monospacedDigit()
            }.width(100)
            TableColumn("情境市值") { ea in
                Text(ea.marketValue.formatted(.number.precision(.fractionLength(0))))
                    .monospacedDigit()
            }.width(100)
            TableColumn("影響") { ea in
                let v = impact(for: ea)
                Text(signedString(v, decimals: 0))
                    .monospacedDigit()
                    .foregroundStyle(v >= 0 ? .green : .red)
            }.width(100)
            TableColumn("影響%") { ea in
                impactPctCell(ea)
            }.width(80)
        }
        .frame(height: min(CGFloat(scenarioAssets.count) * 52 + 44, 400))
    }

    @ViewBuilder
    private func impactPctCell(_ ea: EnrichedAsset) -> some View {
        if let pct = impactPct(for: ea) {
            Text(signedString(pct, decimals: 2) + "%")
                .monospacedDigit()
                .foregroundStyle(pct >= 0 ? .green : .red)
        } else {
            Text("—").foregroundStyle(.secondary)
        }
    }
}

// MARK: - ShockSlider

struct ShockSlider: View {
    let label: String
    @Binding var value: Double
    var range: ClosedRange<Double> = -100...100

    var body: some View {
        VStack(spacing: 2) {
            HStack {
                Text(label).font(.subheadline)
                Spacer()
                Text(valueLabel)
                    .font(.subheadline)
                    .monospacedDigit()
                    .foregroundStyle(value > 0 ? .green : value < 0 ? .red : .secondary)
                    .frame(width: 60, alignment: .trailing)
            }
            Slider(value: $value, in: range, step: 1)
                .tint(value > 0 ? .green : value < 0 ? .red : .secondary)
        }
    }

    private var valueLabel: String {
        let formatted = value.formatted(.number.precision(.fractionLength(0)))
        return (value >= 0 ? "+" : "") + formatted + "%"
    }
}
