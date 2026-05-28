import SwiftUI
import Charts

struct DashboardView: View {
    @Environment(PortfolioStore.self) private var store

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 24) {

                // ── Top metrics ───────────────────────────────────────────
                LazyVGrid(
                    columns: [GridItem(.flexible()), GridItem(.flexible()), GridItem(.flexible())],
                    spacing: 16
                ) {
                    MetricCard(
                        title:    "淨資產 Net Worth",
                        value:    store.netWorth.formatted(.number.precision(.fractionLength(0))),
                        subtitle: store.baseCurrency
                    )
                    MetricCard(
                        title:    "總資產 Total Assets",
                        value:    store.totalAssets.formatted(.number.precision(.fractionLength(0))),
                        subtitle: store.baseCurrency
                    )
                    if let cagr = store.portfolioCagr {
                        MetricCard(
                            title:    "年化報酬 CAGR",
                            value:    (cagr * 100).formatted(.number.precision(.fractionLength(2))) + "%",
                            subtitle: "since earliest purchase",
                            valueColor: cagr >= 0 ? .green : .red
                        )
                    } else {
                        MetricCard(
                            title:    "總負債 Liabilities",
                            value:    store.totalLiabilities.formatted(.number.precision(.fractionLength(0))),
                            subtitle: store.baseCurrency
                        )
                    }
                }

                if store.isRefreshing {
                    HStack {
                        ProgressView().scaleEffect(0.8)
                        Text("正在抓取最新價格…").font(.caption).foregroundStyle(.secondary)
                    }
                }

                // ── Charts ────────────────────────────────────────────────
                if !store.enrichedAssets.isEmpty {
                    Divider()

                    HStack(alignment: .top, spacing: 24) {
                        // Category pie
                        VStack(alignment: .leading, spacing: 8) {
                            Text("資產大類佔比").font(.headline)
                            CategoryPieChart()
                        }
                        .frame(maxWidth: .infinity)

                        // Individual allocation pie
                        VStack(alignment: .leading, spacing: 8) {
                            Text("個別資產配置").font(.headline)
                            AllocationPieChart()
                        }
                        .frame(maxWidth: .infinity)
                    }
                } else if !store.isRefreshing {
                    ContentUnavailableView(
                        "尚無資產",
                        systemImage: "tray",
                        description: Text("請前往「編輯組合」新增資產，再按 Refresh 抓取價格。")
                    )
                }
            }
            .padding()
        }
        .navigationTitle("總覽")
        .toolbar {
            ToolbarItem {
                Picker("幣別", selection: Bindable(store).baseCurrency) {
                    Text("TWD").tag("TWD")
                    Text("USD").tag("USD")
                }
                .pickerStyle(.segmented)
                .frame(width: 120)
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
        .task {
            if store.enrichedAssets.isEmpty {
                await store.refreshPrices()
            }
        }
    }
}

// MARK: - Category Pie Chart

struct CategoryPieChart: View {
    @Environment(PortfolioStore.self) private var store

    struct Slice: Identifiable {
        var id:    String
        var label: String
        var value: Double
    }

    var data: [Slice] {
        let groups: [(String, [AssetCategory])] = [
            ("股票 Stock",      [.stock, .stockTW, .etf]),
            ("加密貨幣 Crypto", [.crypto]),
            ("現金 Cash",       [.cash]),
            ("其他 Other",      [.other]),
        ]
        return groups.compactMap { label, cats in
            let total = store.enrichedAssets
                .filter { cats.contains($0.category) }
                .reduce(0) { $0 + $1.marketValue }
            return total > 0 ? Slice(id: label, label: label, value: total) : nil
        }
    }

    var body: some View {
        Chart(data) { slice in
            SectorMark(
                angle: .value("Value", slice.value),
                innerRadius: .ratio(0.5),
                angularInset: 2
            )
            .foregroundStyle(by: .value("Category", slice.label))
            .cornerRadius(4)
        }
        .chartLegend(position: .trailing, alignment: .center)
        .frame(height: 220)
    }
}

// MARK: - Individual Allocation Pie Chart

struct AllocationPieChart: View {
    @Environment(PortfolioStore.self) private var store

    struct Slice: Identifiable {
        var id:    String
        var label: String
        var value: Double
    }

    var data: [Slice] {
        let total = store.enrichedAssets.reduce(0) { $0 + $1.marketValue }
        guard total > 0 else { return [] }

        let sorted = store.enrichedAssets
            .map { Slice(id: $0.id, label: $0.ticker ?? $0.name, value: $0.marketValue) }
            .sorted { $0.value > $1.value }

        let threshold = total * 0.03
        var visible: [Slice] = []
        var othersValue: Double = 0

        for (idx, slice) in sorted.enumerated() {
            if idx < 9 && slice.value >= threshold {
                visible.append(slice)
            } else {
                othersValue += slice.value
            }
        }
        if othersValue > 0 {
            visible.append(Slice(id: "others", label: "其他", value: othersValue))
        }
        return visible
    }

    var body: some View {
        Chart(data) { slice in
            SectorMark(
                angle: .value("Value", slice.value),
                innerRadius: .ratio(0.5),
                angularInset: 2
            )
            .foregroundStyle(by: .value("Asset", slice.label))
            .cornerRadius(4)
        }
        .chartLegend(position: .trailing, alignment: .center)
        .frame(height: 220)
    }
}

// MARK: - Metric Card

struct MetricCard: View {
    let title:      String
    let value:      String
    var subtitle:   String     = ""
    var valueColor: Color      = .primary

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title)
                .font(.caption)
                .foregroundStyle(.secondary)
            Text(value)
                .font(.title2)
                .fontWeight(.bold)
                .foregroundStyle(valueColor)
            if !subtitle.isEmpty {
                Text(subtitle)
                    .font(.caption2)
                    .foregroundStyle(.tertiary)
            }
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(.background)
        .clipShape(RoundedRectangle(cornerRadius: 12))
        .shadow(color: .black.opacity(0.06), radius: 4, y: 2)
    }
}
