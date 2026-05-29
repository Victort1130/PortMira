import SwiftUI

struct NewsView: View {
    @Environment(PortfolioStore.self) private var store
    @State private var articles:   [NewsArticle] = []
    @State private var isLoading   = false
    @State private var lastRefresh: Date?

    private let defaultTickers = ["SPY", "QQQ", "BTC-USD", "GC=F", "0050.TW"]

    var body: some View {
        Group {
            if isLoading {
                ProgressView("載入新聞中…")
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else if articles.isEmpty {
                ContentUnavailableView(
                    "暫無新聞",
                    systemImage: "newspaper",
                    description: Text("按 Refresh 載入最新財經新聞。")
                )
            } else {
                List(articles) { article in
                    NewsRowView(article: article)
                }
                .listStyle(.inset)
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

    @MainActor
    private func load() async {
        isLoading = true
        let portfolioTickers = store.portfolio.assets
            .compactMap { $0.ticker }
            .filter { !$0.isEmpty }
        let tickers = Array(Set(defaultTickers + portfolioTickers))
        let svc = NewsService()
        articles   = await svc.fetchNews(tickers: tickers)
        lastRefresh = Date()
        isLoading  = false
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
