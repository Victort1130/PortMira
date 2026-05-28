import SwiftUI
import Charts

struct RebalanceView: View {
    @Environment(PortfolioStore.self) private var store

    var actions: [RebalanceAction] {
        CalculationsEngine.calcRebalance(enrichedAssets: store.enrichedAssets)
    }

    var totalTargetPct: Double {
        store.portfolio.assets.compactMap { $0.targetPct }.reduce(0, +)
    }

    var totalValue: Double {
        store.enrichedAssets.reduce(0) { $0 + $1.marketValue }
    }

    var nActions: Int {
        actions.filter { $0.action != "持有 Hold" }.count
    }

    private var targetPctSubtitle: String {
        if abs(totalTargetPct - 100) < 0.1 { return "✓ 合計 100%" }
        let diff = (100 - totalTargetPct).formatted(.number.precision(.fractionLength(1)))
        return "⚠️ 差 \(diff)%"
    }

    var body: some View {
        Group {
            if store.enrichedAssets.isEmpty {
                ContentUnavailableView(
                    "尚無持倉資料",
                    systemImage: "scale.3d",
                    description: Text("請先新增資產並 Refresh 價格。")
                )
            } else if actions.isEmpty {
                ContentUnavailableView(
                    "尚未設定目標比例",
                    systemImage: "scale.3d",
                    description: Text("請前往「編輯組合」，在各資產的 Target % 欄位填入目標配置。")
                )
            } else {
                ScrollView {
                    VStack(alignment: .leading, spacing: 24) {
                        summaryCards
                        Divider()
                        actionsTable
                        Divider()
                        allocationChart
                    }
                    .padding()
                }
            }
        }
        .navigationTitle("再平衡")
    }

    // MARK: - Sub-views

    private var summaryCards: some View {
        LazyVGrid(
            columns: [GridItem(.flexible()), GridItem(.flexible()), GridItem(.flexible())],
            spacing: 16
        ) {
            MetricCard(
                title:    "組合總市值",
                value:    totalValue.formatted(.number.precision(.fractionLength(0))),
                subtitle: store.baseCurrency
            )
            MetricCard(
                title:      "目標比例合計",
                value:      totalTargetPct.formatted(.number.precision(.fractionLength(1))) + "%",
                subtitle:   targetPctSubtitle,
                valueColor: abs(totalTargetPct - 100) < 0.1 ? .green : .orange
            )
            MetricCard(
                title:    "需要操作",
                value:    "\(nActions) 筆",
                subtitle: "買入或賣出"
            )
        }
    }

    private var actionsTable: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("操作建議").font(.headline)
            Text("按調整幅度排序，優先處理偏差最大的資產。")
                .font(.caption).foregroundStyle(.secondary)

            RebalanceTable(actions: actions)
        }
    }

    private var allocationChart: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("目前 vs 目標配置").font(.headline)

            Chart {
                ForEach(actions) { action in
                    BarMark(
                        x: .value("資產", action.asset.ticker ?? action.asset.name),
                        y: .value("佔比", action.currentPct)
                    )
                    .foregroundStyle(by: .value("類型", "目前配置"))
                    .position(by: .value("類型", "目前配置"))
                    BarMark(
                        x: .value("資產", action.asset.ticker ?? action.asset.name),
                        y: .value("佔比", action.targetPct)
                    )
                    .foregroundStyle(by: .value("類型", "目標配置"))
                    .position(by: .value("類型", "目標配置"))
                }
            }
            .chartForegroundStyleScale([
                "目前配置": Color.gray.opacity(0.5),
                "目標配置": Color.indigo,
            ])
            .chartYAxis {
                AxisMarks { value in
                    AxisGridLine()
                    AxisTick()
                    AxisValueLabel {
                        if let d = value.as(Double.self) {
                            Text(d.formatted(.number.precision(.fractionLength(0))) + "%")
                        }
                    }
                }
            }
            .chartLegend(position: .top, alignment: .trailing)
            .frame(height: 260)
        }
    }
}

// MARK: - Rebalance table (isolated scope for @TableColumnBuilder)

private struct RebalanceTable: View {
    let actions: [RebalanceAction]

    private func actionColor(_ action: RebalanceAction) -> Color {
        if action.action.contains("買") { return .green }
        if action.action.contains("賣") { return .red }
        return .secondary
    }

    var body: some View {
        Table(actions) {
            TableColumn("資產名稱") { a in
                VStack(alignment: .leading, spacing: 2) {
                    Text(a.asset.name).fontWeight(.medium)
                    Text(a.asset.ticker ?? "—").font(.caption).foregroundStyle(.secondary)
                }
            }
            TableColumn("目前佔比") { a in
                Text(a.currentPct.formatted(.number.precision(.fractionLength(1))) + "%")
                    .monospacedDigit()
            }.width(80)
            TableColumn("目標佔比") { a in
                Text(a.targetPct.formatted(.number.precision(.fractionLength(1))) + "%")
                    .monospacedDigit()
            }.width(80)
            TableColumn("調整金額") { a in
                Text(a.deltaValue.formatted(.number.precision(.fractionLength(0))))
                    .monospacedDigit()
                    .foregroundStyle(a.deltaValue >= 0 ? .green : .red)
            }.width(110)
            TableColumn("調整數量") { a in
                deltaUnitsCell(a)
            }.width(100)
            TableColumn("操作") { a in
                Text(a.action)
                    .foregroundStyle(actionColor(a))
                    .fontWeight(.medium)
            }.width(90)
        }
        .frame(height: min(CGFloat(actions.count) * 52 + 44, 400))
    }

    @ViewBuilder
    private func deltaUnitsCell(_ a: RebalanceAction) -> some View {
        if let units = a.deltaUnits {
            Text(units.formatted(.number.precision(.fractionLength(4))))
                .monospacedDigit()
                .foregroundStyle(units >= 0 ? .green : .red)
        } else {
            Text("—").foregroundStyle(.secondary)
        }
    }
}
