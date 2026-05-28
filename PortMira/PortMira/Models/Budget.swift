import Foundation

enum ExpenseCategory: String, Codable, CaseIterable, Identifiable {
    var id: String { rawValue }
    case food = "餐飲"
    case transport = "交通"
    case subscription = "訂閱服務"
    case entertainment = "娛樂"
    case investment = "投資支出"
    case medical = "醫療"
    case shopping = "購物"
    case other = "其他"

    var icon: String {
        switch self {
        case .food: return "fork.knife"
        case .transport: return "car"
        case .subscription: return "repeat"
        case .entertainment: return "gamecontroller"
        case .investment: return "chart.line.uptrend.xyaxis"
        case .medical: return "cross.case"
        case .shopping: return "bag"
        case .other: return "ellipsis.circle"
        }
    }
}

enum BudgetPeriod: String, Codable, CaseIterable, Identifiable {
    var id: String { rawValue }
    case monthly = "月"
    case biweekly = "雙週"
    case weekly = "週"
}

struct Expense: Codable, Identifiable {
    var id: String
    var date: String   // "YYYY-MM-DD"
    var category: ExpenseCategory
    var amount: Double
    var currency: String
    var note: String
}

struct Budget: Codable, Identifiable {
    var id: String
    var categoryName: String   // ExpenseCategory.rawValue or "總計"
    var amount: Double
    var currency: String
    var period: BudgetPeriod
    var alertThreshold: Double  // 0.0–1.0

    enum CodingKeys: String, CodingKey {
        case id, amount, currency, period, alertThreshold = "alert_threshold"
        case categoryName = "category"
    }
}

struct BudgetData: Codable {
    var budgets: [Budget]
    var expenses: [Expense]
}

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
