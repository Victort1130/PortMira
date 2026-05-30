import Foundation

// MARK: - Expense Category

enum ExpenseCategory: String, Codable, CaseIterable, Identifiable {
    var id: String { rawValue }
    case food          = "餐飲"
    case transport     = "交通"
    case subscription  = "訂閱服務"
    case entertainment = "娛樂"
    case investment    = "投資支出"
    case medical       = "醫療"
    case shopping      = "購物"
    case other         = "其他"

    var icon: String {
        switch self {
        case .food:          return "fork.knife"
        case .transport:     return "car"
        case .subscription:  return "repeat"
        case .entertainment: return "gamecontroller"
        case .investment:    return "chart.line.uptrend.xyaxis"
        case .medical:       return "cross.case"
        case .shopping:      return "bag"
        case .other:         return "ellipsis.circle"
        }
    }
}

// MARK: - Budget Period

enum BudgetPeriod: String, Codable, CaseIterable, Identifiable {
    var id: String { rawValue }
    case monthly  = "月"
    case biweekly = "雙週"
    case weekly   = "週"
}

// MARK: - Card Network

enum CardNetwork: String, Codable, CaseIterable, Identifiable {
    var id: String { rawValue }
    case visa       = "Visa"
    case mastercard = "Mastercard"
    case jcb        = "JCB"
    case unionPay   = "UnionPay"
    case amex       = "Amex"
    case other      = "其他"

    var icon: String {
        switch self {
        case .visa:       return "v.square.fill"
        case .mastercard: return "m.square.fill"
        case .jcb:        return "j.square.fill"
        case .unionPay:   return "u.square.fill"
        case .amex:       return "a.square.fill"
        case .other:      return "creditcard.fill"
        }
    }
}

// MARK: - Card Type

enum CardType: String, Codable, CaseIterable, Identifiable {
    var id: String { rawValue }
    case credit = "credit"
    case debit  = "debit"

    var displayName: String { self == .credit ? "信用卡" : "簽帳金融卡" }
}

// MARK: - PaymentCard

struct PaymentCard: Codable, Identifiable, Hashable {
    var id: String
    var cardName: String
    var bank: String
    var network: CardNetwork
    var cardTier: String
    var lastFour: String
    var cardType: CardType
    var linkedLiabilityId: String?
    var isDefault: Bool

    var displayName: String { "\(bank) \(cardName) ···\(lastFour)" }

    enum CodingKeys: String, CodingKey {
        case id, bank, network
        case cardName          = "card_name"
        case cardTier          = "card_tier"
        case lastFour          = "last_four"
        case cardType          = "card_type"
        case linkedLiabilityId = "linked_liability_id"
        case isDefault         = "is_default"
    }
}

// MARK: - Expense

struct Expense: Codable, Identifiable {
    var id: String
    var date: String   // "YYYY-MM-DD"
    var category: ExpenseCategory
    var amount: Double
    var currency: String
    var note: String
    var paymentCardId: String?   // nil = cash

    enum CodingKeys: String, CodingKey {
        case id, date, category, amount, currency, note
        case paymentCardId = "payment_card_id"
    }
}

// MARK: - Budget

struct Budget: Codable, Identifiable {
    var id: String
    var categoryName: String
    var amount: Double
    var currency: String
    var period: BudgetPeriod
    var alertThreshold: Double

    enum CodingKeys: String, CodingKey {
        case id, amount, currency, period
        case categoryName   = "category"
        case alertThreshold = "alert_threshold"
    }
}

// MARK: - BudgetData (persisted file)

struct BudgetData: Codable {
    var budgets:  [Budget]
    var expenses: [Expense]
    var cards:    [PaymentCard]

    init(budgets: [Budget] = [], expenses: [Expense] = [], cards: [PaymentCard] = []) {
        self.budgets  = budgets
        self.expenses = expenses
        self.cards    = cards
    }

    // Custom decoder so `cards` is optional (backward-compat with old files)
    init(from decoder: Decoder) throws {
        let c   = try decoder.container(keyedBy: CodingKeys.self)
        budgets  = try c.decode([Budget].self,  forKey: .budgets)
        expenses = try c.decode([Expense].self, forKey: .expenses)
        cards    = (try c.decodeIfPresent([PaymentCard].self, forKey: .cards)) ?? []
    }

    enum CodingKeys: String, CodingKey {
        case budgets, expenses, cards
    }
}

// MARK: - BudgetStatus

struct BudgetStatus: Identifiable {
    let id: String
    let categoryName: String
    let icon: String
    let budgetAmount: Double
    let spentAmount: Double
    let remaining: Double
    let pctUsed: Double
    let isAlert: Bool
    let period: BudgetPeriod
}
