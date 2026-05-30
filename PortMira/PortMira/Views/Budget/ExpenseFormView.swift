import SwiftUI

struct ExpenseFormView: View {
    @Environment(BudgetStore.self) var budgetStore
    @Environment(\.dismiss) var dismiss

    var editing: Expense? = nil

    @State private var date:          Date            = Date()
    @State private var category:      ExpenseCategory = .food
    @State private var amount:        Double          = 0
    @State private var currency:      String          = "TWD"
    @State private var note:          String          = ""
    @State private var paymentCardId: String?         = nil

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

                Picker("付款方式", selection: $paymentCardId) {
                    Label("現金", systemImage: "banknote").tag(nil as String?)
                    ForEach(budgetStore.cards) { card in
                        Label(card.displayName, systemImage: card.network.icon).tag(card.id as String?)
                    }
                }

                TextField("備註（選填）", text: $note)
            }
            .navigationTitle(isEditing ? "編輯支出" : "新增支出")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("取消") { dismiss() } }
                ToolbarItem(placement: .confirmationAction) {
                    Button("儲存") { save() }.disabled(amount <= 0)
                }
            }
        }
        .frame(minWidth: 320, minHeight: 340)
        .onAppear { prefill() }
    }

    private func prefill() {
        guard let e = editing else {
            // Pre-select default card for new expenses
            paymentCardId = budgetStore.cards.first(where: { $0.isDefault })?.id
            return
        }
        let fmt = DateFormatter(); fmt.dateFormat = "yyyy-MM-dd"
        date          = fmt.date(from: e.date) ?? Date()
        category      = e.category
        amount        = e.amount
        currency      = e.currency
        note          = e.note
        paymentCardId = e.paymentCardId
    }

    private func save() {
        let fmt = DateFormatter(); fmt.dateFormat = "yyyy-MM-dd"
        let expense = Expense(
            id:            editing?.id ?? "exp_\(UUID().uuidString.prefix(8))",
            date:          fmt.string(from: date),
            category:      category,
            amount:        amount,
            currency:      currency,
            note:          note,
            paymentCardId: paymentCardId
        )
        if editing != nil { budgetStore.updateExpense(expense) }
        else              { budgetStore.addExpense(expense) }
        dismiss()
    }
}
