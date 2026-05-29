import SwiftUI

struct ExpenseFormView: View {
    @Environment(BudgetStore.self) var budgetStore
    @Environment(\.dismiss) var dismiss

    var editing: Expense? = nil

    @State private var date = Date()
    @State private var category: ExpenseCategory = .food
    @State private var amount: Double = 0
    @State private var currency = "TWD"
    @State private var note = ""

    private var isEditing: Bool { editing != nil }

    var body: some View {
        NavigationStack {
            Form {
                DatePicker("日期", selection: $date, displayedComponents: .date)
                Picker("類別", selection: $category) {
                    ForEach(ExpenseCategory.allCases) { cat in
                        Label(cat.rawValue, systemImage: cat.icon).tag(cat)
                    }
                }
                TextField("金額", value: $amount, format: .number)
                Picker("幣別", selection: $currency) {
                    ForEach(["TWD", "USD", "EUR", "JPY", "GBP"], id: \.self) { Text($0).tag($0) }
                }
                TextField("備註（選填）", text: $note)
            }
            .navigationTitle(isEditing ? "編輯支出" : "新增支出")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("取消") { dismiss() } }
                ToolbarItem(placement: .confirmationAction) {
                    Button("儲存") { save() }
                        .disabled(amount <= 0)
                }
            }
        }
        .frame(minWidth: 320, minHeight: 300)
        .onAppear { prefill() }
    }

    private func prefill() {
        guard let e = editing else { return }
        let fmt = DateFormatter(); fmt.dateFormat = "yyyy-MM-dd"
        date = fmt.date(from: e.date) ?? Date()
        category = e.category
        amount = e.amount
        currency = e.currency
        note = e.note
    }

    private func save() {
        let fmt = DateFormatter(); fmt.dateFormat = "yyyy-MM-dd"
        let dateStr = fmt.string(from: date)
        if let existing = editing {
            budgetStore.updateExpense(Expense(
                id: existing.id,
                date: dateStr,
                category: category,
                amount: amount,
                currency: currency,
                note: note
            ))
        } else {
            budgetStore.addExpense(Expense(
                id: "exp_\(UUID().uuidString.prefix(8))",
                date: dateStr,
                category: category,
                amount: amount,
                currency: currency,
                note: note
            ))
        }
        dismiss()
    }
}
