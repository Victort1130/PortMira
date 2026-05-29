import Foundation

struct NewsArticle: Identifiable, Decodable, Sendable {
    let uuid:                String
    let title:               String
    let publisher:           String
    let link:                String
    let providerPublishTime: Int

    var id: String { uuid }

    var publishDate: Date { Date(timeIntervalSince1970: Double(providerPublishTime)) }

    var relativeTimeString: String {
        let interval = Date().timeIntervalSince(publishDate)
        if interval < 3600  { return "\(Int(interval / 60))分鐘前" }
        if interval < 86400 { return "\(Int(interval / 3600))小時前" }
        return "\(Int(interval / 86400))天前"
    }
}

actor NewsService {

    // Fetch news for each ticker and aggregate (deduplicated, newest-first)
    func fetchNews(tickers: [String]) async -> [NewsArticle] {
        let uniqueTickers = Array(Set(tickers)).prefix(12)
        var allArticles: [NewsArticle] = []

        await withTaskGroup(of: [NewsArticle].self) { group in
            for ticker in uniqueTickers {
                group.addTask {
                    (try? await self.fetchArticles(for: ticker)) ?? []
                }
            }
            for await articles in group {
                allArticles.append(contentsOf: articles)
            }
        }

        var seen = Set<String>()
        return allArticles
            .filter { seen.insert($0.uuid).inserted }
            .sorted { $0.providerPublishTime > $1.providerPublishTime }
    }

    private func fetchArticles(for ticker: String) async throws -> [NewsArticle] {
        let encoded = ticker.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? ticker
        let urlStr = "https://query1.finance.yahoo.com/v1/finance/search?q=\(encoded)&newsCount=6&quotesCount=0"
        guard let url = URL(string: urlStr) else { return [] }
        var req = URLRequest(url: url, timeoutInterval: 10)
        req.setValue("Mozilla/5.0", forHTTPHeaderField: "User-Agent")
        let (data, _) = try await URLSession.shared.data(for: req)

        struct SearchResponse: Decodable {
            struct Article: Decodable {
                let uuid:                String?
                let title:               String?
                let publisher:           String?
                let link:                String?
                let providerPublishTime: Int?
                let type:                String?
            }
            let news: [Article]?
        }

        let resp = try JSONDecoder().decode(SearchResponse.self, from: data)
        return (resp.news ?? []).compactMap { a in
            guard let uuid = a.uuid,
                  let title = a.title,
                  let publisher = a.publisher,
                  let link = a.link,
                  let time = a.providerPublishTime,
                  a.type == "STORY"
            else { return nil }
            return NewsArticle(uuid: uuid, title: title, publisher: publisher,
                               link: link, providerPublishTime: time)
        }
    }
}
