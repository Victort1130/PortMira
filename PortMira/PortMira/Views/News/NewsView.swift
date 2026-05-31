import SwiftUI

// MARK: - Category

enum NewsCategory: String, CaseIterable, Identifiable {
    var id: String { rawValue }
    case portfolio = "個股"
    case market    = "市場"
    case macro     = "總體經濟"

    var icon: String {
        switch self {
        case .portfolio: return "chart.line.uptrend.xyaxis"
        case .market:    return "globe.americas"
        case .macro:     return "building.columns"
        }
    }
}

// MARK: - View

struct NewsView: View {
    @Environment(PortfolioStore.self) private var store

    @State private var selectedCategory:  NewsCategory   = .portfolio
    @State private var portfolioArticles: [NewsArticle]  = []
    @State private var marketArticles:    [NewsArticle]  = []
    @State private var macroArticles:     [NewsArticle]  = []
    @State private var isLoading                         = false
    @State private var lastRefresh:       Date?

    private let marketTickers: [String] = ["SPY", "QQQ", "BTC-USD", "GC=F", "0050.TW"]
    private let macroTickers:  [String] = ["^TNX", "^VIX", "DX-Y.NYB", "^GSPC", "^N225"]

    private var displayed: [NewsArticle] {
        switch selectedCategory {
        case .portfolio: return portfolioArticles
        case .market:    return marketArticles
        case .macro:     return macroArticles
        }
    }

    var body: some View {
        VStack(spacing: 0) {
            Picker("類別", selection: $selectedCategory) {
                ForEach(NewsCategory.allCases) { cat in
                    Label(cat.rawValue, systemImage: cat.icon).tag(cat)
                }
            }
            .pickerStyle(.segmented)
            .padding(.horizontal, 16)
            .padding(.vertical, 8)

            Divider()

            Group {
                if isLoading {
                    ProgressView("載入新聞中…")
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else if displayed.isEmpty {
                    emptyState
                } else {
                    List(displayed) { article in
                        NewsRowView(article: article)
                    }
                    .listStyle(.inset)
                }
            }
        }
        .navigationTitle("財經新聞")
        .toolbar {
            ToolbarItem {
                if let date = lastRefresh {
                    Text(date.formatted(.dateTime.hour().minute()))
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            ToolbarItem {
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

    @ViewBuilder
    private var emptyState: some View {
        if selectedCategory == .portfolio &&
           store.portfolio.assets.compactMap({ $0.ticker }).isEmpty {
            ContentUnavailableView(
                "尚無持倉代號",
                systemImage: "newspaper",
                description: Text("在「編輯組合」為資產填入代號後即可載入個股新聞。")
            )
        } else {
            ContentUnavailableView(
                "暫無新聞",
                systemImage: "newspaper",
                description: Text("按 Refresh 載入最新財經新聞。")
            )
        }
    }

    @MainActor
    private func load() async {
        isLoading = true
        let portfolioTickers = store.portfolio.assets
            .compactMap { $0.ticker }
            .filter { !$0.isEmpty }

        // Three separate actor instances → concurrent fetch
        async let pFetch  = NewsService().fetchNews(tickers: portfolioTickers)
        async let mFetch  = NewsService().fetchNews(tickers: marketTickers)
        async let mcFetch = NewsService().fetchNews(tickers: macroTickers)

        (portfolioArticles, marketArticles, macroArticles) = await (pFetch, mFetch, mcFetch)
        lastRefresh = Date()
        isLoading   = false
    }
}

// MARK: - Row

private struct NewsRowView: View {
    let article: NewsArticle
    @Environment(\.openURL) private var openURL

    var body: some View {
        Button {
            if let url = URL(string: article.link) { openURL(url) }
        } label: {
            VStack(alignment: .leading, spacing: 4) {
                Text(article.title)
                    .font(.body)
                    .foregroundStyle(.primary)
                    .lineLimit(3)
                    .multilineTextAlignment(.leading)

                HStack {
                    Text(article.publisher)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Spacer()
                    Text(article.relativeTimeString)
                        .font(.caption)
                        .foregroundStyle(.tertiary)
                }
            }
            .padding(.vertical, 4)
        }
        .buttonStyle(.plain)
    }
}
