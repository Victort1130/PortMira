import SwiftUI

struct HoldingsView: View {
    @Environment(PortfolioStore.self) private var store
    @State private var showCagr  = false
    @State private var sortOrder = [KeyPathComparator(\EnrichedAsset.marketValue, order: .reverse)]

    var body: some View {
        VStack(spacing: 0) {
            if store.enrichedAssets.isEmpty {
                ContentUnavailableView(
                    "尚無持倉資料",
                    systemImage: "chart.bar.xaxis",
                    description: Text("新增資產並按 Refresh 後即可看到持倉明細。")
                )
            } else {
                if showCagr {
                    AssetsTableWithCagr(sortOrder: $sortOrder)
                } else {
                    AssetsTableBase(sortOrder: $sortOrder)
                }

                Divider()

                if !store.portfolio.liabilities.isEmpty {
                    LiabilitiesTable()
                }
            }
        }
        .navigationTitle("持倉明細")
        .toolbar {
            ToolbarItem {
                Toggle(isOn: $showCagr) {
                    Label("CAGR", systemImage: "calendar.badge.clock")
                }
                .toggleStyle(.button)
                .help("顯示/隱藏年化報酬率欄位")
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
}

// MARK: - Asset table (without CAGR)

private struct AssetsTableBase: View {
    @Environment(PortfolioStore.self) private var store
    @Binding var sortOrder: [KeyPathComparator<EnrichedAsset>]

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
        }
    }
}

// MARK: - Asset table (with CAGR)

private struct AssetsTableWithCagr: View {
    @Environment(PortfolioStore.self) private var store
    @Binding var sortOrder: [KeyPathComparator<EnrichedAsset>]

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
            TableColumn("年化報酬 CAGR") { ea in
                plPctText(ea.cagr)
            }.width(120)
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
