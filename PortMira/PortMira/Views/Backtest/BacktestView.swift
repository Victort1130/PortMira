import SwiftUI
import Charts

struct BacktestView: View {
    @Environment(PortfolioStore.self) var store
    @State private var startDate = Calendar.current.date(byAdding: .year, value: -3, to: Date()) ?? Date()
    @State private var endDate = Date()
    @State private var benchmarkLabel = "SPY（S&P 500）"
    @State private var result: BacktestResult?
    @State private var isRunning = false
    @State private var errorMessage: String?

    private let benchmarkOptions = ["SPY（S&P 500）", "QQQ（NASDAQ 100）", "0050.TW（台股50）", "不設基準"]
    private let benchmarkTickers: [String: String] = [
        "SPY（S&P 500）": "SPY",
        "QQQ（NASDAQ 100）": "QQQ",
        "0050.TW（台股50）": "0050.TW"
    ]

    var body: some View {
        HSplitView {
            // Controls
            VStack(alignment: .leading, spacing: 16) {
                Text("回測設定").font(.headline)
                DatePicker("開始日期", selection: $startDate, displayedComponents: .date)
                DatePicker("結束日期", selection: $endDate, in: startDate..., displayedComponents: .date)
                Picker("基準指數", selection: $benchmarkLabel) {
                    ForEach(benchmarkOptions, id: \.self) { Text($0).tag($0) }
                }
                Text("ℹ️ 僅含有代碼的資產（股票、ETF、加密貨幣）會納入計算")
                    .font(.caption).foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
                Button {
                    Task { await runBacktest() }
                } label: {
                    if isRunning {
                        ProgressView().controlSize(.small)
                    } else {
                        Label("執行回測", systemImage: "play.fill")
                    }
                }
                .buttonStyle(.borderedProminent)
                .disabled(isRunning)
                Spacer()
            }
            .padding()
            .frame(minWidth: 240, maxWidth: 280)

            // Results
            ScrollView {
                if let err = errorMessage {
                    ContentUnavailableView("回測失敗", systemImage: "exclamationmark.triangle", description: Text(err))
                        .padding()
                } else if let r = result {
                    BacktestResultView(result: r)
                        .padding()
                } else {
                    ContentUnavailableView("尚未執行", systemImage: "chart.xyaxis.line", description: Text("設定日期範圍後點擊「執行回測」"))
                        .padding()
                }
            }
        }
        .navigationTitle("回測工具")
    }

    private func runBacktest() async {
        isRunning = true
        errorMessage = nil
        let engine = BacktestEngine()
        let bm = benchmarkLabel == "不設基準" ? nil : benchmarkTickers[benchmarkLabel]
        do {
            result = try await engine.run(
                assets: store.portfolio.assets,
                startDate: startDate,
                endDate: endDate,
                fxRates: store.fxRates,
                benchmark: bm
            )
        } catch {
            errorMessage = error.localizedDescription
        }
        isRunning = false
    }
}

struct BacktestResultView: View {
    let result: BacktestResult

    struct ChartPoint: Identifiable {
        let id = UUID()
        let date: String
        let value: Double
        let series: String

        private static let df: DateFormatter = {
            let f = DateFormatter(); f.dateFormat = "yyyy-MM-dd"; return f
        }()
        var dateValue: Date { Self.df.date(from: date) ?? Date() }
    }

    var chartData: [ChartPoint] {
        var data = result.dates.enumerated().map { (i, d) in
            ChartPoint(date: d, value: result.portfolioValues[i], series: "我的組合")
        }
        if let bm = result.benchmarkValues, let bmName = result.benchmark {
            data += result.dates.enumerated().compactMap { (i, d) in
                guard let v = bm[i] else { return nil }
                return ChartPoint(date: d, value: v, series: bmName)
            }
        }
        return data
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            // Metrics
            HStack(spacing: 12) {
                BacktestMetricCard(title: "總報酬率", value: result.totalReturn.asPercentString(), color: result.totalReturn >= 0 ? .green : .red)
                BacktestMetricCard(title: "年化報酬 (CAGR)", value: result.cagr.asPercentString(), color: result.cagr >= 0 ? .green : .red)
                BacktestMetricCard(title: "最大回撤", value: "-\(result.maxDrawdown.asPercentString())", color: .red)
            }

            if !result.skipped.isEmpty {
                Text("略過資產：\(result.skipped.joined(separator: "、"))")
                    .font(.caption).foregroundStyle(.secondary)
            }

            // Chart
            if !chartData.isEmpty {
                Chart(chartData) { d in
                    LineMark(x: .value("日期", d.dateValue), y: .value("價值", d.value))
                        .foregroundStyle(by: .value("系列", d.series))
                }
                .frame(height: 250)
                .chartLegend(position: .top, alignment: .leading)
            }

            // Per-asset returns
            if !result.assetReturns.isEmpty {
                Text("各資產報酬率").font(.headline)
                ForEach(result.assetReturns, id: \.ticker) { r in
                    HStack {
                        Text(r.name).font(.subheadline)
                        Spacer()
                        Text(r.ticker).font(.caption).foregroundStyle(.secondary)
                        Text(r.returnPct.asPercentString())
                            .font(.subheadline.monospacedDigit())
                            .foregroundStyle(r.returnPct >= 0 ? .green : .red)
                    }
                    Divider()
                }
            }
        }
    }
}

struct BacktestMetricCard: View {
    let title: String
    let value: String
    var color: Color = .primary

    var body: some View {
        GroupBox {
            VStack(alignment: .leading) {
                Text(title).font(.caption).foregroundStyle(.secondary)
                Text(value).font(.title3.bold().monospacedDigit()).foregroundStyle(color)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }
}

private extension Double {
    func asPercentString() -> String {
        String(format: "%.1f%%", self * 100)
    }
}
