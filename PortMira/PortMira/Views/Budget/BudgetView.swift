import SwiftUI

struct BudgetView: View {
    @Environment(BudgetStore.self) var budgetStore
    @Environment(PortfolioStore.self) var portfolioStore
    @State private var showAddExpense = false
    @State private var showSettings = false

    var statuses: [BudgetStatus] {
        budgetStore.calcBudgetStatuses(
            fxRates: portfolioStore.fxRates,
            baseCurrency: portfolioStore.baseCurrency
        )
    }

    var alerts: [BudgetStatus] { statuses.filter { $0.isAlert } }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                // Alert banner
                if !alerts.isEmpty {
                    HStack {
                        Image(systemName: "exclamationmark.triangle.fill")
                            .foregroundStyle(.orange)
                        Text("預算警示：\(alerts.map(\.categoryName).joined(separator: "、")) 已超過設定閾值")
                            .font(.subheadline)
                    }
                    .padding()
                    .background(.orange.opacity(0.15))
                    .cornerRadius(8)
                }

                // Budget overview
                if statuses.isEmpty {
                    ContentUnavailableView("尚未設定預算", systemImage: "creditcard", description: Text("點擊右上角「設定」新增預算"))
                } else {
                    ForEach(statuses) { s in
                        BudgetProgressCard(status: s, baseCurrency: portfolioStore.baseCurrency)
                    }
                }

                // Recent expenses
                Divider()
                Text("近期支出").font(.headline)
                if budgetStore.expenses.isEmpty {
                    Text("尚無支出記錄").foregroundStyle(.secondary)
                } else {
                    let sorted = budgetStore.expenses.sorted { $0.date > $1.date }
                    List {
                        ForEach(sorted.prefix(20)) { e in
                            ExpenseRow(expense: e)
                        }
                        .onDelete { offsets in
                            let idsToDelete = offsets.map { sorted[$0].id }
                            let indicesToDelete = IndexSet(
                                idsToDelete.compactMap { id in
                                    budgetStore.expenses.firstIndex(where: { $0.id == id })
                                }
                            )
                            budgetStore.deleteExpenses(at: indicesToDelete)
                        }
                    }
                    .listStyle(.plain)
                    .frame(minHeight: 44, maxHeight: CGFloat(min(sorted.count, 20)) * 44)
                }
            }
            .padding()
        }
        .navigationTitle("預算追蹤")
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Button("設定") { showSettings = true }
            }
            ToolbarItem {
                Button { showAddExpense = true } label: {
                    Label("新增支出", systemImage: "plus")
                }
            }
        }
        .sheet(isPresented: $showAddExpense) {
            ExpenseFormView()
                .environment(budgetStore)
        }
        .sheet(isPresented: $showSettings) {
            BudgetSettingsView()
                .environment(budgetStore)
        }
    }
}

struct BudgetProgressCard: View {
    let status: BudgetStatus
    let baseCurrency: String

    var progressColor: Color {
        if status.pctUsed < 0.6 { return .green }
        if status.pctUsed < 0.85 { return .orange }
        return .red
    }

    var body: some View {
        GroupBox {
            VStack(alignment: .leading, spacing: 6) {
                HStack {
                    Label(status.categoryName, systemImage: status.icon)
                        .font(.subheadline.weight(.semibold))
                    Spacer()
                    Text(status.period.rawValue)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    if status.isAlert {
                        Image(systemName: "exclamationmark.triangle.fill")
                            .foregroundStyle(.orange)
                            .font(.caption)
                    }
                }
                ProgressView(value: min(status.pctUsed, 1.0))
                    .tint(progressColor)
                HStack {
                    Text("已花 \(status.spentAmount, format: .number.precision(.fractionLength(0))) \(baseCurrency)")
                        .font(.caption)
                        .foregroundStyle(progressColor)
                    Spacer()
                    Text("預算 \(status.budgetAmount, format: .number.precision(.fractionLength(0)))")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
        }
    }
}

struct ExpenseRow: View {
    let expense: Expense
    var body: some View {
        HStack {
            Image(systemName: expense.category.icon)
                .frame(width: 20)
                .foregroundStyle(.secondary)
            VStack(alignment: .leading, spacing: 2) {
                Text(expense.category.rawValue).font(.subheadline)
                if !expense.note.isEmpty {
                    Text(expense.note).font(.caption).foregroundStyle(.secondary)
                }
            }
            Spacer()
            VStack(alignment: .trailing) {
                Text("\(expense.amount, format: .number.precision(.fractionLength(0))) \(expense.currency)")
                    .font(.subheadline.monospacedDigit())
                Text(expense.date).font(.caption).foregroundStyle(.secondary)
            }
        }
        .padding(.vertical, 2)
    }
}
