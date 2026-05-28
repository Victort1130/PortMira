import SwiftUI

struct BudgetSettingsView: View {
    @Environment(BudgetStore.self) var budgetStore
    @Environment(\.dismiss) var dismiss

    @State private var newCategoryName = "餐飲"
    @State private var newAmount: Double = 10000
    @State private var newCurrency = "TWD"
    @State private var newPeriod: BudgetPeriod = .monthly
    @State private var newThreshold: Double = 0.6

    var body: some View {
        NavigationStack {
            List {
                Section("現有預算") {
                    if budgetStore.budgets.isEmpty {
                        Text("尚無預算設定").foregroundStyle(.secondary)
                    }
                    ForEach(budgetStore.budgets) { b in
                        HStack {
                            VStack(alignment: .leading) {
                                Text(b.categoryName).font(.subheadline.weight(.semibold))
                                Text("\(b.amount, format: .number.precision(.fractionLength(0))) \(b.currency) / \(b.period.rawValue)・警示 \(b.alertThreshold * 100, format: .number.precision(.fractionLength(0)))%")
                                    .font(.caption).foregroundStyle(.secondary)
                            }
                            Spacer()
                        }
                    }
                    .onDelete { offsets in
                        offsets.forEach { i in budgetStore.deleteBudget(id: budgetStore.budgets[i].id) }
                    }
                }

                Section("新增預算") {
                    Picker("類別", selection: $newCategoryName) {
                        Text("總計").tag("總計")
                        ForEach(ExpenseCategory.allCases) { c in Text(c.rawValue).tag(c.rawValue) }
                    }
                    HStack {
                        Text("金額")
                        Spacer()
                        TextField("金額", value: $newAmount, format: .number)
                            .multilineTextAlignment(.trailing)
                            .frame(width: 100)
                    }
                    Picker("幣別", selection: $newCurrency) {
                        ForEach(["TWD", "USD", "EUR", "JPY", "GBP"], id: \.self) { Text($0).tag($0) }
                    }
                    Picker("週期", selection: $newPeriod) {
                        ForEach(BudgetPeriod.allCases) { Text($0.rawValue).tag($0) }
                    }
                    VStack(alignment: .leading) {
                        Text("警示閾值：\(newThreshold * 100, format: .number.precision(.fractionLength(0)))%")
                        Slider(value: $newThreshold, in: 0.1...1.0, step: 0.05)
                    }
                    Button("新增預算") {
                        budgetStore.addBudget(Budget(
                            id: "bgt_\(UUID().uuidString.prefix(8))",
                            categoryName: newCategoryName,
                            amount: newAmount,
                            currency: newCurrency,
                            period: newPeriod,
                            alertThreshold: newThreshold
                        ))
                    }
                    .buttonStyle(.borderedProminent)
                }
            }
            .navigationTitle("預算設定")
            .toolbar {
                ToolbarItem(placement: .confirmationAction) { Button("完成") { dismiss() } }
            }
        }
        .frame(minWidth: 400, minHeight: 500)
    }
}
