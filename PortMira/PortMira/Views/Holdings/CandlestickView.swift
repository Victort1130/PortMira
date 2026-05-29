import SwiftUI
import Charts

// MARK: - Data Model

struct OHLCVBar: Identifiable {
    let id = UUID()
    let date: Date
    let open: Double
    let high: Double
    let low: Double
    let close: Double
    let volume: Double

    var isGreen: Bool { close >= open }
}

// MARK: - Service

actor CandlestickService {
    func fetchOHLCV(ticker: String) async throws -> [OHLCVBar] {
        let encodedTicker = ticker.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? ticker
        let urlStr = "https://query1.finance.yahoo.com/v8/finance/chart/\(encodedTicker)?interval=1d&range=3mo"
        guard let url = URL(string: urlStr) else { throw CandlestickError.invalidURL }

        var req = URLRequest(url: url, timeoutInterval: 20)
        req.setValue("Mozilla/5.0", forHTTPHeaderField: "User-Agent")
        let (data, _) = try await URLSession.shared.data(for: req)

        struct ChartResponse: Decodable {
            struct Chart: Decodable {
                struct Result: Decodable {
                    let timestamp: [Int]?
                    struct Indicators: Decodable {
                        struct Quote: Decodable {
                            let open:   [Double?]?
                            let high:   [Double?]?
                            let low:    [Double?]?
                            let close:  [Double?]?
                            let volume: [Double?]?
                        }
                        let quote: [Quote]
                    }
                    let indicators: Indicators
                }
                let result: [Result]?
                struct Error: Decodable { let code: String; let description: String }
                let error: Error?
            }
            let chart: Chart
        }

        let resp = try JSONDecoder().decode(ChartResponse.self, from: data)

        if let err = resp.chart.error {
            throw CandlestickError.apiError(err.description)
        }

        guard let result = resp.chart.result?.first,
              let timestamps = result.timestamp,
              let quote = result.indicators.quote.first,
              let opens   = quote.open,
              let highs   = quote.high,
              let lows    = quote.low,
              let closes  = quote.close,
              let volumes = quote.volume
        else {
            throw CandlestickError.noData
        }

        let count = min(timestamps.count, opens.count, highs.count, lows.count, closes.count, volumes.count)
        var bars: [OHLCVBar] = []
        for i in 0..<count {
            guard let o = opens[i], let h = highs[i], let l = lows[i],
                  let c = closes[i], let v = volumes[i] else { continue }
            let date = Date(timeIntervalSince1970: Double(timestamps[i]))
            bars.append(OHLCVBar(date: date, open: o, high: h, low: l, close: c, volume: v))
        }
        return bars
    }
}

enum CandlestickError: LocalizedError {
    case invalidURL
    case noData
    case apiError(String)

    var errorDescription: String? {
        switch self {
        case .invalidURL:       return "無效的 URL"
        case .noData:           return "無法取得 OHLCV 資料"
        case .apiError(let m):  return m
        }
    }
}

// MARK: - SMA helpers

private func sma(_ values: [Double], period: Int) -> [Double?] {
    guard period > 0 else { return values.map { _ in nil } }
    return values.indices.map { i in
        guard i >= period - 1 else { return nil }
        let slice = values[(i - period + 1)...i]
        return slice.reduce(0, +) / Double(period)
    }
}

// MARK: - Main View

struct CandlestickView: View {
    let asset: Asset

    @State private var bars:       [OHLCVBar] = []
    @State private var isLoading:  Bool       = false
    @State private var errorMsg:   String?    = nil
    @State private var showSMA20:  Bool       = true
    @State private var showSMA50:  Bool       = true

    private var closes: [Double] { bars.map(\.close) }
    private var sma20: [Double?] { sma(closes, period: 20) }
    private var sma50: [Double?] { sma(closes, period: 50) }

    // Pairs of (bar, sma20?, sma50?) zipped for overlay marks
    private var overlayData: [(bar: OHLCVBar, sma20: Double?, sma50: Double?)] {
        zip(bars, zip(sma20, sma50)).map { (bar, pair) in
            (bar, pair.0, pair.1)
        }
    }

    var body: some View {
        VStack(spacing: 0) {
            if isLoading {
                ProgressView("載入中…")
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else if let err = errorMsg {
                VStack(spacing: 12) {
                    Image(systemName: "exclamationmark.triangle")
                        .font(.largeTitle)
                        .foregroundStyle(.orange)
                    Text(err).foregroundStyle(.secondary)
                    Button("重試") { Task { await load() } }
                        .buttonStyle(.borderedProminent)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else if bars.isEmpty {
                ContentUnavailableView("無資料", systemImage: "chart.xyaxis.line")
            } else {
                ScrollView {
                    VStack(spacing: 16) {
                        candlestickChart
                        volumeChart
                    }
                    .padding()
                }
            }
        }
        .navigationTitle("\(asset.name) — K 線圖（3 個月）")
        .toolbar {
            ToolbarItemGroup {
                Toggle(isOn: $showSMA20) {
                    Label("SMA 20", systemImage: "chart.line.flattrend.xyaxis")
                }
                .toggleStyle(.button)
                .tint(.orange)
                .help("顯示/隱藏 20 日均線")

                Toggle(isOn: $showSMA50) {
                    Label("SMA 50", systemImage: "chart.line.flattrend.xyaxis")
                }
                .toggleStyle(.button)
                .tint(.blue)
                .help("顯示/隱藏 50 日均線")

                Button {
                    Task { await load() }
                } label: {
                    Label("Refresh", systemImage: "arrow.clockwise")
                }
                .disabled(isLoading)
            }
        }
        .task { await load() }
    }

    // MARK: - Candlestick chart

    private var candlestickChart: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("價格 K 線")
                .font(.headline)

            Chart {
                // Candle bodies
                ForEach(bars) { bar in
                    RectangleMark(
                        x: .value("Date", bar.date),
                        yStart: .value("Body Low",  min(bar.open, bar.close)),
                        yEnd:   .value("Body High", max(bar.open, bar.close)),
                        width: .fixed(6)
                    )
                    .foregroundStyle(bar.isGreen ? Color.green : Color.red)
                }
                // Wicks
                ForEach(bars) { bar in
                    RuleMark(
                        x: .value("Date", bar.date),
                        yStart: .value("Low",  bar.low),
                        yEnd:   .value("High", bar.high)
                    )
                    .lineStyle(StrokeStyle(lineWidth: 1.5))
                    .foregroundStyle(bar.isGreen ? Color.green : Color.red)
                }
                // SMA 20
                if showSMA20 {
                    ForEach(overlayData.indices, id: \.self) { i in
                        let item = overlayData[i]
                        if let v = item.sma20 {
                            LineMark(
                                x: .value("Date", item.bar.date),
                                y: .value("SMA20", v)
                            )
                            .foregroundStyle(Color.orange)
                            .lineStyle(StrokeStyle(lineWidth: 1.5))
                            .interpolationMethod(.linear)
                        }
                    }
                }
                // SMA 50
                if showSMA50 {
                    ForEach(overlayData.indices, id: \.self) { i in
                        let item = overlayData[i]
                        if let v = item.sma50 {
                            LineMark(
                                x: .value("Date", item.bar.date),
                                y: .value("SMA50", v)
                            )
                            .foregroundStyle(Color.blue)
                            .lineStyle(StrokeStyle(lineWidth: 1.5))
                            .interpolationMethod(.linear)
                        }
                    }
                }
            }
            .chartXAxis {
                AxisMarks(values: .stride(by: .month)) {
                    AxisGridLine()
                    AxisTick()
                    AxisValueLabel(format: .dateTime.month(.abbreviated))
                }
            }
            .chartYAxis { AxisMarks(position: .trailing) }
            .frame(height: 320)
        }
    }

    // MARK: - Volume chart

    private var volumeChart: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("成交量")
                .font(.headline)

            Chart {
                ForEach(bars) { bar in
                    BarMark(
                        x: .value("Date",   bar.date),
                        y: .value("Volume", bar.volume),
                        width: .fixed(6)
                    )
                    .foregroundStyle(bar.isGreen ? Color.green.opacity(0.7) : Color.red.opacity(0.7))
                }
            }
            .chartXAxis {
                AxisMarks(values: .stride(by: .month)) {
                    AxisGridLine()
                    AxisTick()
                    AxisValueLabel(format: .dateTime.month(.abbreviated))
                }
            }
            .chartYAxis { AxisMarks(position: .trailing) }
            .frame(height: 120)
        }
    }

    // MARK: - Load

    private func load() async {
        guard let ticker = asset.ticker, !ticker.isEmpty else {
            errorMsg = "此資產沒有交易代號，無法取得 K 線資料。"
            return
        }
        isLoading = true
        errorMsg  = nil
        defer { isLoading = false }
        do {
            let svc = CandlestickService()
            bars = try await svc.fetchOHLCV(ticker: ticker)
            if bars.isEmpty { errorMsg = "查無資料（\(ticker)）" }
        } catch {
            errorMsg = error.localizedDescription
        }
    }
}
