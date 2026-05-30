import Foundation
import Observation
import SwiftUI

@Observable
final class BudgetStore {
    var budgets:  [Budget]      = []
    var expenses: [Expense]     = []
    var cards:    [PaymentCard] = []
    var lastError: String?

    private var fileURL: URL {
        let support = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
        let dir = support.appendingPathComponent("PortMira", isDirectory: true)
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        return dir.appendingPathComponent("budget_data.json")
    }

    init() { load() }

    // MARK: - Persistence

    func load() {
        guard FileManager.default.fileExists(atPath: fileURL.path) else { return }
        do {
            let data    = try Data(contentsOf: fileURL)
            let decoded = try JSONDecoder().decode(BudgetData.self, from: data)
            budgets  = decoded.budgets
            expenses = decoded.expenses
            cards    = decoded.cards
        } catch {
            lastError = "載入失敗：\(error.localizedDescription)"
        }
    }

    func save() {
        guard let encoded = try? JSONEncoder().encode(
            BudgetData(budgets: budgets, expenses: expenses, cards: cards)
        ) else { return }
        let url = fileURL
        Task.detached {
            do { try encoded.write(to: url, options: .atomic) }
            catch { print("[BudgetStore] save error: \(error)") }
        }
    }

    // MARK: - Expense CRUD

    func addExpense(_ expense: Expense) {
        expenses.append(expense)
        save()
    }

    func deleteExpenses(at offsets: IndexSet) {
        expenses.remove(atOffsets: offsets)
        save()
    }

    func updateExpense(_ expense: Expense) {
        guard let idx = expenses.firstIndex(where: { $0.id == expense.id }) else { return }
        expenses[idx] = expense
        save()
    }

    // MARK: - Budget CRUD

    func addBudget(_ budget: Budget) {
        budgets.append(budget)
        save()
    }

    func deleteBudget(id: String) {
        budgets.removeAll { $0.id == id }
        save()
    }

    func updateBudget(_ budget: Budget) {
        guard let idx = budgets.firstIndex(where: { $0.id == budget.id }) else { return }
        budgets[idx] = budget
        save()
    }

    // MARK: - Card CRUD

    func addCard(_ card: PaymentCard) {
        if card.isDefault { clearOtherDefaults(except: card.id) }
        cards.append(card)
        save()
    }

    func updateCard(_ card: PaymentCard) {
        guard let idx = cards.firstIndex(where: { $0.id == card.id }) else { return }
        if card.isDefault { clearOtherDefaults(except: card.id) }
        cards[idx] = card
        save()
    }

    func deleteCard(id: String) {
        cards.removeAll { $0.id == id }
        save()
    }

    private func clearOtherDefaults(except id: String) {
        for i in cards.indices where cards[i].isDefault && cards[i].id != id {
            cards[i].isDefault = false
        }
    }

    // MARK: - Budget calculations

    func calcBudgetStatuses(fxRates: [String: Double], baseCurrency: String) -> [BudgetStatus] {
        budgets.map { b in
            let periodExpenses = currentPeriodExpenses(for: b)
            let fxB        = fxRates[b.currency] ?? 1.0
            let budgetBase = b.amount * fxB
            let spentBase  = periodExpenses.reduce(0.0) { acc, e in
                acc + e.amount * (fxRates[e.currency] ?? 1.0)
            }
            let pct  = budgetBase > 0 ? spentBase / budgetBase : 0.0
            let icon = ExpenseCategory(rawValue: b.categoryName)?.icon ?? "creditcard"
            return BudgetStatus(
                id:           b.id,
                categoryName: b.categoryName,
                icon:         icon,
                budgetAmount: budgetBase,
                spentAmount:  spentBase,
                remaining:    budgetBase - spentBase,
                pctUsed:      pct,
                isAlert:      pct >= b.alertThreshold,
                period:       b.period
            )
        }
    }

    func currentPeriodExpenses(for budget: Budget) -> [Expense] {
        let start = periodStart(budget.period)
        let fmt   = DateFormatter()
        fmt.dateFormat = "yyyy-MM-dd"
        let startStr = fmt.string(from: start)
        let todayStr = fmt.string(from: Date())
        return expenses.filter { e in
            e.date >= startStr &&
            e.date <= todayStr &&
            (budget.categoryName == "總計" || e.category.rawValue == budget.categoryName)
        }
    }

    private func periodStart(_ period: BudgetPeriod) -> Date {
        let cal   = Calendar.current
        let today = Date()
        switch period {
        case .weekly:
            return cal.dateInterval(of: .weekOfYear, for: today)?.start ?? today
        case .biweekly:
            let weekStart = cal.dateInterval(of: .weekOfYear, for: today)?.start ?? today
            let weekNum   = cal.component(.weekOfYear, from: today)
            return weekNum % 2 == 0
                ? cal.date(byAdding: .weekOfYear, value: -1, to: weekStart)!
                : weekStart
        case .monthly:
            return cal.dateInterval(of: .month, for: today)?.start ?? today
        }
    }
}
