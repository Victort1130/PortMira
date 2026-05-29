import SwiftUI

struct HoldingsView: View {
    @Environment(PortfolioStore.self) private var store
    @State private var showCagr              = false
    @State private var showIndicators        = false
    @State private var showStats             = false
    @State private var indicators:           [IndicatorResult] = []
    @State private var isLoadingIndicators   = false
    @State private var sortOrder = [KeyPathComparator(\EnrichedAsset.marketValue, order: .reverse)]
    @State private var selectedAssetForChart: Asset? = nil

    var body: some View {
        VStack(spacing: 0) {
            if store.enrichedAssets.isEmpty {
                ContentUnavailableView(
                    "尚無持倉資料",
                    systemImage: "chart.bar.xaxis",
                    description: Text("新增資產並按 Refresh 後即可看到持倉明細。")
                )
            } else {
                // Portfolio Statistics disclosure group
                if showStats {
                    VStack(alignment: .leading, spacing: 8) {
                        HStack {
                            Label("組合統計", systemImage: "ruler")
                                .font(.headline)
                                .padding(.horizontal)
                                .padding(.top, 12)
                            Spacer()
                            Button {
                                withAnimation { showStats = false }
                            } label: {
                                Image(systemName: "chevron.up")
                                    .foregroundStyle(.secondary)
                            }
                            .buttonStyle(.plain)
                            .padding(.trailing)
                            .padding(.top, 12)
                        }
                        PortfolioStatsView()
                            .padding(.bottom, 12)
                        Divider()
                    }
                }

                if showCagr {
                    AssetsTableWithCagr(sortOrder: $sortOrder, selectedAsset: $selectedAssetForChart)
                } else {
                    AssetsTableBase(sortOrder: $sortOrder, selectedAsset: $selectedAssetForChart)
                }

                Divider()

                if !store.portfolio.liabilities.isEmpty {
                    LiabilitiesTable()
                }

                if showIndicators {
                    Divider()
                    IndicatorsTable(indicators: indicators, isLoading: isLoadingIndicators)
                }
            }
        }
        .navigationTitle("持倉明細")
        .onChange(of: showIndicators) { _, newValue in
            if newValue { Task { await loadIndicators() } }
        }
        .sheet(item: $selectedAssetForChart) { asset in
            NavigationStack {
                CandlestickView(asset: asset)
                    .toolbar {
                        ToolbarItem(placement: .cancellationAction) {
                            Button("關閉") { selectedAssetForChart = nil }
                        }
                    }
            }
            .frame(minWidth: 700, minHeight: 600)
        }
        .toolbar {
            ToolbarItem {
                Toggle(isOn: $showStats.animation()) {
                    Label("組合統計", systemImage: "ruler")
                }
                .toggleStyle(.button)
                .help("顯示/隱藏組合統計面板")
            }
            ToolbarItem {
                Toggle(isOn: $showCagr) {
                    Label("CAGR", systemImage: "calendar.badge.clock")
                }
                .toggleStyle(.button)
                .help("顯示/隱藏年化報酬率欄位")
            }
            ToolbarItem {
                Button {
                    showIndicators.toggle()
                } label: {
                    Label("技術指標", systemImage: "chart.line.uptrend.xyaxis")
                }
                .help("顯示/隱藏 RSI 與 MACD 技術指標")
            }
            ToolbarItem {
                Button {
                    Task { await store.refreshPrices() }
                } label: {
                    Label("Refresh", systemImage: "arrow.clockwise")
                }
                .disabled(store.isRefreshing)
            }
        }
    }

    @MainActor
    private func loadIndicators() async {
        isLoadingIndicators = true
        let assets = store.portfolio.assets   // snapshot on MainActor before suspending
        let svc = TechnicalIndicatorService()
        indicators = await svc.fetchAll(assets: assets)
        isLoadingIndicators = false
    }
}

// MARK: - Asset table (without CAGR)

private struct AssetsTableBase: View {
    @Environment(PortfolioStore.self) private var store
    @Binding var sortOrder: [KeyPathComparator<EnrichedAsset>]
    @Binding var selectedAsset: Asset?

    var body: some View {
        Table(store.enrichedAssets, sortOrder: $sortOrder) {
            TableColumn("資產名稱", value: \.name) { ea in
                VStack(alignment: .leading, spacing: 2) {
                    Text(ea.name).fontWeight(.medium)
                    Text(ea.category.displayName).font(.caption).foregroundStyle(.secondary)
                }
            }
            TableColumn("代號") { ea in
                Text(ea.ticker ?? "—").foregroundStyle(.secondary)
            }.width(80)
            TableColumn("數量") { ea in
                Text(ea.quantity.formatted(.number.precision(.fractionLength(4)))).monospacedDigit()
            }.width(90)
            TableColumn("現價") { ea in
                Text(ea.currentPrice.formatted(.number.precision(.fractionLength(2)))).monospacedDigit()
            }.width(90)
            TableColumn("市值", value: \.marketValue) { ea in
                Text(ea.marketValue.formatted(.number.precision(.fractionLength(0)))).monospacedDigit()
            }.width(110)
            TableColumn("總成本", value: \.costBasis) { ea in
                Text(ea.costBasis.formatted(.number.precision(.fractionLength(0))))
                    .monospacedDigit().foregroundStyle(.secondary)
            }.width(110)
            TableColumn("未實現損益", value: \.unrealizedPL) { ea in
                Text(ea.unrealizedPL.formatted(.number.precision(.fractionLength(0))))
                    .monospacedDigit()
                    .foregroundStyle(ea.unrealizedPL >= 0 ? .green : .red)
            }.width(110)
            TableColumn("損益%") { ea in
                plPctText(ea.unrealizedPLPct)
            }.width(80)
            TableColumn("日變動%") { ea in
                plPctText(ea.dailyChangePct)
            }.width(80)
            TableColumn("K 線") { ea in
                Button {
                    selectedAsset = ea.asset
                } label: {
                    Image(systemName: "chart.candlestick")
                }
                .buttonStyle(.borderless)
                .disabled(ea.ticker == nil || ea.ticker!.isEmpty)
                .help("查看 K 線圖")
            }.width(50)
        }
    }
}

// MARK: - Asset table (with CAGR)

private struct AssetsTableWithCagr: View {
    @Environment(PortfolioStore.self) private var store
    @Binding var sortOrder: [KeyPathComparator<EnrichedAsset>]
    @Binding var selectedAsset: Asset?

    var body: some View {
        Table(store.enrichedAssets, sortOrder: $sortOrder) {
            TableColumn("資產名稱", value: \.name) { ea in
                VStack(alignment: .leading, spacing: 2) {
                    Text(ea.name).fontWeight(.medium)
                    Text(ea.category.displayName).font(.caption).foregroundStyle(.secondary)
                }
            }
            TableColumn("代號") { ea in
                Text(ea.ticker ?? "—").foregroundStyle(.secondary)
            }.width(80)
            TableColumn("數量") { ea in
                Text(ea.quantity.formatted(.number.precision(.fractionLength(4)))).monospacedDigit()
            }.width(90)
            TableColumn("現價") { ea in
                Text(ea.currentPrice.formatted(.number.precision(.fractionLength(2)))).monospacedDigit()
            }.width(90)
            TableColumn("市值", value: \.marketValue) { ea in
                Text(ea.marketValue.formatted(.number.precision(.fractionLength(0)))).monospacedDigit()
            }.width(110)
            TableColumn("總成本", value: \.costBasis) { ea in
                Text(ea.costBasis.formatted(.number.precision(.fractionLength(0))))
                    .monospacedDigit().foregroundStyle(.secondary)
            }.width(110)
            TableColumn("未實現損益", value: \.unrealizedPL) { ea in
                Text(ea.unrealizedPL.formatted(.number.precision(.fractionLength(0))))
                    .monospacedDigit()
                    .foregroundStyle(ea.unrealizedPL >= 0 ? .green : .red)
            }.width(110)
            TableColumn("損益%") { ea in
                plPctText(ea.unrealizedPLPct)
            }.width(80)
            Group {
                TableColumn("日變動%") { (ea: EnrichedAsset) in
                    plPctText(ea.dailyChangePct)
                }.width(80)
                TableColumn("年化報酬 CAGR") { (ea: EnrichedAsset) in
                    plPctText(ea.cagr)
                }.width(120)
                TableColumn("K 線") { (ea: EnrichedAsset) in
                    Button {
                        selectedAsset = ea.asset
                    } label: {
                        Image(systemName: "chart.candlestick")
                    }
                    .buttonStyle(.borderless)
                    .disabled(ea.ticker == nil || ea.ticker!.isEmpty)
                    .help("查看 K 線圖")
                }.width(50)
            }
        }
    }
}

// MARK: - Liabilities table

private struct LiabilitiesTable: View {
    @Environment(PortfolioStore.self) private var store

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("負債明細")
                .font(.headline)
                .padding(.horizontal)
                .padding(.top, 12)

            Table(store.portfolio.liabilities) {
                TableColumn("名稱",   value: \.name)
                TableColumn("類別") { Text($0.category.displayName) }.width(100)
                TableColumn("金額") { liab in
                    Text(liab.amount.formatted(.number.precision(.fractionLength(0)))).monospacedDigit()
                }.width(110)
                TableColumn("幣別") { Text($0.currency.rawValue) }.width(60)
                TableColumn("年利率") { liab in
                    if let r = liab.annualRate {
                        Text((r * 100).formatted(.number.precision(.fractionLength(2))) + "%")
                    } else {
                        Text("—")
                    }
                }.width(80)
            }
            .frame(height: min(CGFloat(store.portfolio.liabilities.count) * 44 + 40, 200))
        }
    }
}

// MARK: - Shared helper

private func plPctText(_ value: Double?) -> some View {
    Group {
        if let v = value {
            Text((v * 100).formatted(.number.precision(.fractionLength(2))) + "%")
                .monospacedDigit()
                .foregroundStyle(v >= 0 ? .green : .red)
        } else {
            Text("—").foregroundStyle(.secondary)
        }
    }
}

// MARK: - Technical Indicators Table

private struct IndicatorsTable: View {
    let indicators: [IndicatorResult]
    let isLoading:  Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text("技術指標（RSI 14 / MACD 12-26-9）").font(.headline)
                Spacer()
                Text("數值僅供參考，不構成買賣建議")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            .padding(.horizontal)
            .padding(.top, 12)

            if isLoading {
                ProgressView("計算中…")
                    .frame(maxWidth: .infinity)
                    .padding()
            } else if indicators.isEmpty {
                Text("無可計算指標的資產（需有 ticker 的股票、ETF、加密貨幣或大宗商品）")
                    .foregroundStyle(.secondary)
                    .padding()
            } else {
                Table(indicators) {
                    TableColumn("名稱", value: \.name)
                    TableColumn("代碼", value: \.ticker)
                    TableColumn("RSI") { r in
                        Text(r.rsi.map { String(format: "%.1f", $0) } ?? "—")
                            .monospacedDigit()
                            .foregroundStyle(rsiColor(r.rsi))
                    }
                    .width(60)
                    TableColumn("RSI 狀態", value: \.rsiContext)
                    .width(100)
                    TableColumn("MACD") { r in
                        Text(r.macd.map { String(format: "%.4f", $0) } ?? "—")
                            .monospacedDigit()
                    }
                    .width(90)
                    TableColumn("MACD 狀態", value: \.macdContext)
                    .width(120)
                }
                .frame(minHeight: 200,
                       maxHeight: min(CGFloat(indicators.count) * 44 + 44, 360))
            }
        }
    }

    private func rsiColor(_ rsi: Double?) -> Color {
        guard let r = rsi else { return .primary }
        if r >= 70 { return .red }
        if r <= 30 { return .green }
        return .primary
    }
}
