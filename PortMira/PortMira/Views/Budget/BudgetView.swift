import SwiftUI

struct BudgetView: View {
    @Environment(BudgetStore.self) var budgetStore
    @Environment(PortfolioStore.self) var portfolioStore
    @State private var showAddExpense    = false
    @State private var showSettings      = false
    @State private var showCardManager   = false
    @State private var editingExpense:   Expense? = nil

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

                // Expenses split by current month vs history
                Divider()
                Text("支出明細").font(.headline)

                let allSorted = budgetStore.expenses.sorted { $0.date > $1.date }
                let curMonthStart = currentMonthStart()
                let thisMonth = allSorted.filter { $0.date >= curMonthStart }
                let older     = allSorted.filter { $0.date < curMonthStart }

                let monthLabel = monthDisplayLabel()
                Text(monthLabel).font(.subheadline).foregroundStyle(.secondary)

                if thisMonth.isEmpty {
                    Text("本月尚無支出記錄").foregroundStyle(.secondary).font(.caption)
                } else {
                    expenseList(thisMonth)
                }

                if !older.isEmpty {
                    DisclosureGroup("歷史記錄（共 \(older.count) 筆）") {
                        let byYear = Dictionary(grouping: older) { String($0.date.prefix(4)) }
                        ForEach(byYear.keys.sorted(by: >), id: \.self) { yr in
                            let yearExpenses = byYear[yr]!
                            DisclosureGroup("📅 \(yr) 年（\(yearExpenses.count) 筆）") {
                                let byMonth = Dictionary(grouping: yearExpenses) { String($0.date.prefix(7)) }
                                ForEach(byMonth.keys.sorted(by: >), id: \.self) { ym in
                                    let mo = String(ym.split(separator: "-").last ?? "")
                                    let moExpenses = byMonth[ym]!.sorted { $0.date > $1.date }
                                    DisclosureGroup("\(mo) 月（\(moExpenses.count) 筆）") {
                                        expenseList(moExpenses)
                                    }
                                    .padding(.leading, 8)
                                }
                            }
                        }
                    }
                    .font(.subheadline)
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
                Button { showCardManager = true } label: {
                    Label("我的卡片", systemImage: "creditcard.viewfinder")
                }
                .help("管理信用卡 / 金融卡")
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
        .sheet(item: $editingExpense) { expense in
            ExpenseFormView(editing: expense)
                .environment(budgetStore)
        }
        .sheet(isPresented: $showSettings) {
            BudgetSettingsView()
                .environment(budgetStore)
        }
        .sheet(isPresented: $showCardManager) {
            CardManagementView()
                .environment(budgetStore)
                .environment(portfolioStore)
        }
    }

    // MARK: - Helpers

    private func currentMonthStart() -> String {
        let fmt = DateFormatter(); fmt.dateFormat = "yyyy-MM-dd"
        let cal = Calendar.current
        let start = cal.dateInterval(of: .month, for: Date())?.start ?? Date()
        return fmt.string(from: start)
    }

    private func monthDisplayLabel() -> String {
        let fmt = DateFormatter(); fmt.dateFormat = "yyyy 年 MM 月"
        return fmt.string(from: Date())
    }

    @ViewBuilder
    private func expenseList(_ expenses: [Expense]) -> some View {
        List {
            ForEach(expenses) { e in
                ExpenseRow(expense: e)
                    .contentShape(Rectangle())
                    .onTapGesture { editingExpense = e }
                    .swipeActions(edge: .trailing) {
                        Button(role: .destructive) {
                            if let idx = budgetStore.expenses.firstIndex(where: { $0.id == e.id }) {
                                budgetStore.deleteExpenses(at: IndexSet([idx]))
                            }
                        } label: { Label("刪除", systemImage: "trash") }
                        Button { editingExpense = e } label: { Label("編輯", systemImage: "pencil") }
                            .tint(.blue)
                    }
            }
        }
        .listStyle(.plain)
        .frame(minHeight: 44, maxHeight: max(CGFloat(expenses.count) * 56, 280))
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
    @Environment(BudgetStore.self) var budgetStore
    let expense: Expense

    private var paymentCard: PaymentCard? {
        guard let id = expense.paymentCardId else { return nil }
        return budgetStore.cards.first { $0.id == id }
    }

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
            VStack(alignment: .trailing, spacing: 2) {
                Text("\(expense.amount, format: .number.precision(.fractionLength(0))) \(expense.currency)")
                    .font(.subheadline.monospacedDigit())
                HStack(spacing: 4) {
                    Text(expense.date).font(.caption).foregroundStyle(.secondary)
                    if let card = paymentCard {
                        Text("···\(card.lastFour)")
                            .font(.caption2)
                            .padding(.horizontal, 4).padding(.vertical, 1)
                            .background(.secondary.opacity(0.12))
                            .clipShape(RoundedRectangle(cornerRadius: 3))
                    } else {
                        Text("現金").font(.caption2).foregroundStyle(.tertiary)
                    }
                }
            }
        }
        .padding(.vertical, 2)
    }
}
