import Foundation
import Observation
import SwiftUI

@Observable
@MainActor
class PortfolioStore {
    var portfolio:      Portfolio      = Portfolio()
    var enrichedAssets: [EnrichedAsset] = []
    var fxRates:        [String: Double] = [:]
    var isRefreshing:   Bool           = false
    var lastError:      String?        = nil

    var baseCurrency: String = UserDefaults.standard.string(forKey: "baseCurrency") ?? "TWD" {
        didSet {
            UserDefaults.standard.set(baseCurrency, forKey: "baseCurrency")
            Task { await reEnrichForCurrency() }
        }
    }

    private var cachedPrices:     [String: Double] = [:]
    private var cachedPrevCloses: [String: Double] = [:]

    // MARK: - Computed

    var totalAssets: Double {
        enrichedAssets.reduce(0) { $0 + $1.marketValue }
    }

    var totalLiabilities: Double {
        portfolio.liabilities.reduce(0) {
            $0 + $1.amount * (fxRates[$1.currency.rawValue] ?? 1.0)
        }
    }

    var netWorth: Double { totalAssets - totalLiabilities }

    var portfolioCagr: Double? {
        CalculationsEngine.portfolioCagr(enrichedAssets: enrichedAssets)
    }

    // MARK: - File URL

    private let fileName = "portfolio.json"

    private var fileURL: URL {
        let support = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
        let dir = support.appendingPathComponent("PortMira", isDirectory: true)
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        return dir.appendingPathComponent(fileName)
    }

    init() {
        load()
    }

    // MARK: - Persistence

    func load() {
        guard FileManager.default.fileExists(atPath: fileURL.path) else { return }
        do {
            let data = try Data(contentsOf: fileURL)
            portfolio = try JSONDecoder().decode(Portfolio.self, from: data)
        } catch {
            print("[PortfolioStore] load error: \(error)")
        }
    }

    func save() {
        do {
            portfolio.meta.lastUpdated = DateFormatter.yyyyMMdd.string(from: Date())
            let encoder = JSONEncoder()
            encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
            let data = try encoder.encode(portfolio)
            try data.write(to: fileURL, options: .atomic)
        } catch {
            print("[PortfolioStore] save error: \(error)")
        }
    }

    // MARK: - Price refresh

    func refreshPrices() async {
        guard !portfolio.assets.isEmpty else { return }
        isRefreshing = true
        lastError    = nil
        defer { isRefreshing = false }

        let (prices, prevCloses) = await PriceService.fetchAll(assets: portfolio.assets)
        cachedPrices     = prices
        cachedPrevCloses = prevCloses

        let fx = await fetchFX()
        fxRates        = fx
        enrichedAssets = CalculationsEngine.enrich(
            assets:       portfolio.assets,
            prices:       prices,
            prevCloses:   prevCloses,
            fxRates:      fx,
            baseCurrency: baseCurrency
        )
    }

    // Re-enrich with existing prices after currency switch (no new network price fetch needed)
    private func reEnrichForCurrency() async {
        guard !cachedPrices.isEmpty else { return }
        let fx = await fetchFX()
        fxRates        = fx
        enrichedAssets = CalculationsEngine.enrich(
            assets:       portfolio.assets,
            prices:       cachedPrices,
            prevCloses:   cachedPrevCloses,
            fxRates:      fx,
            baseCurrency: baseCurrency
        )
    }

    private func fetchFX() async -> [String: Double] {
        let currencies = Set(
            portfolio.assets.map { $0.currency.rawValue } +
            portfolio.liabilities.map { $0.currency.rawValue }
        )
        return await PriceService.fetchFXRates(
            currencies: Array(currencies),
            base: baseCurrency
        )
    }

    // MARK: - Asset helpers

    func addAsset(_ asset: Asset) {
        portfolio.assets.append(asset)
        save()
    }

    func updateAsset(_ asset: Asset) {
        guard let idx = portfolio.assets.firstIndex(where: { $0.id == asset.id }) else { return }
        portfolio.assets[idx] = asset
        save()
    }

    func deleteAssets(at offsets: IndexSet) {
        portfolio.assets.remove(atOffsets: offsets)
        save()
    }

    // MARK: - Liability helpers

    func addLiability(_ liability: Liability) {
        portfolio.liabilities.append(liability)
        save()
    }

    func updateLiability(_ liability: Liability) {
        guard let idx = portfolio.liabilities.firstIndex(where: { $0.id == liability.id }) else { return }
        portfolio.liabilities[idx] = liability
        save()
    }

    func deleteLiabilities(at offsets: IndexSet) {
        portfolio.liabilities.remove(atOffsets: offsets)
        save()
    }

    // MARK: - Scenario helpers

    func saveScenario(_ scenario: Scenario) {
        if let idx = portfolio.scenarios.firstIndex(where: { $0.id == scenario.id }) {
            portfolio.scenarios[idx] = scenario
        } else {
            portfolio.scenarios.append(scenario)
        }
        save()
    }

    func deleteScenario(_ scenario: Scenario) {
        portfolio.scenarios.removeAll { $0.id == scenario.id }
        save()
    }
}

// MARK: - DateFormatter helper

extension DateFormatter {
    static let yyyyMMdd: DateFormatter = {
        let f = DateFormatter()
        f.dateFormat = "yyyy-MM-dd"
        return f
    }()
}
