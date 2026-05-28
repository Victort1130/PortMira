import Foundation

// MARK: - Asset

struct Asset: Codable, Identifiable {
    var id: String
    var name: String
    var category: AssetCategory
    var ticker: String?
    var quantity: Double
    var costPerUnit: Double
    var currency: Currency
    var purchaseDate: String?
    var targetPct: Double?
    var note: String?

    enum CodingKeys: String, CodingKey {
        case id, name, category, ticker, quantity
        case costPerUnit = "cost_per_unit"
        case currency
        case purchaseDate = "purchase_date"
        case targetPct   = "target_pct"
        case note
    }
}

// MARK: - Liability

struct Liability: Codable, Identifiable {
    var id: String
    var name: String
    var category: LiabilityCategory
    var amount: Double
    var currency: Currency
    var annualRate: Double?
    var note: String?

    enum CodingKeys: String, CodingKey {
        case id, name, category, amount, currency
        case annualRate = "annual_rate"
        case note
    }
}

// MARK: - Scenario

struct Scenario: Codable, Identifiable, Hashable {
    var id: String
    var name: String
    var createdAt: String
    var shocks: ScenarioShocks

    enum CodingKeys: String, CodingKey {
        case id, name, shocks
        case createdAt = "created_at"
    }
}

struct ScenarioShocks: Codable, Hashable {
    var categories: [String: Double]
    var fx: [String: Double]
}

// MARK: - Portfolio (top-level document)

struct Portfolio: Codable {
    var assets: [Asset]
    var liabilities: [Liability]
    var scenarios: [Scenario]
    var meta: PortfolioMeta

    init() {
        assets      = []
        liabilities = []
        scenarios   = []
        meta        = PortfolioMeta()
    }
}

struct PortfolioMeta: Codable {
    var lastUpdated: String
    var version: String

    init() {
        lastUpdated = ""
        version     = "0.2.0"
    }

    enum CodingKeys: String, CodingKey {
        case lastUpdated = "last_updated"
        case version
    }
}

// MARK: - Enums

enum AssetCategory: String, Codable, CaseIterable {
    case stock     = "stock"
    case stockTW   = "stock_tw"
    case etf       = "etf"
    case crypto    = "crypto"
    case commodity = "commodity"
    case cash      = "cash"
    case other     = "other"

    var displayName: String {
        switch self {
        case .stock:     return "US Stock"
        case .stockTW:   return "TW Stock"
        case .etf:       return "ETF"
        case .crypto:    return "Crypto"
        case .commodity: return "Commodity"
        case .cash:      return "Cash"
        case .other:     return "Other"
        }
    }

    var isAutoPrice: Bool {
        switch self {
        case .stock, .stockTW, .etf, .crypto, .commodity: return true
        case .cash, .other:                                return false
        }
    }

    var icon: String {
        switch self {
        case .stock:     return "chart.line.uptrend.xyaxis"
        case .stockTW:   return "building.columns"
        case .etf:       return "chart.bar.fill"
        case .crypto:    return "bitcoinsign.circle"
        case .commodity: return "chart.bar.fill"
        case .cash:      return "banknote"
        case .other:     return "ellipsis.circle"
        }
    }
}

enum LiabilityCategory: String, Codable, CaseIterable {
    case creditCard     = "credit_card"
    case loan           = "loan"
    case marginLoan     = "margin_loan"
    case otherLiability = "other_liability"

    var displayName: String {
        switch self {
        case .creditCard:     return "Credit Card"
        case .loan:           return "Loan"
        case .marginLoan:     return "Margin Loan"
        case .otherLiability: return "Other"
        }
    }
}

enum Currency: String, Codable, CaseIterable {
    case twd = "TWD"
    case usd = "USD"
    case eur = "EUR"
    case jpy = "JPY"
    case gbp = "GBP"
}
