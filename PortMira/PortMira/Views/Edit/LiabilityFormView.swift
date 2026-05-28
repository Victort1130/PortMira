import SwiftUI

struct LiabilityFormView: View {
    @Environment(PortfolioStore.self) private var store
    @Environment(\.dismiss) private var dismiss

    var existing: Liability? = nil

    @State private var name:       String            = ""
    @State private var category:   LiabilityCategory = .creditCard
    @State private var amount:     Double            = 0
    @State private var currency:   Currency          = .twd
    @State private var annualRate: Double            = 0
    @State private var hasRate:    Bool              = false
    @State private var note:       String            = ""

    var body: some View {
        Form {
            Section("基本資訊") {
                TextField("名稱", text: $name)
                Picker("類別", selection: $category) {
                    ForEach(LiabilityCategory.allCases, id: \.self) {
                        Text($0.displayName).tag($0)
                    }
                }
            }

            Section("金額") {
                HStack {
                    Text("金額")
                    Spacer()
                    TextField("0", value: $amount, format: .number)
                        .multilineTextAlignment(.trailing)
                }
                Picker("幣別", selection: $currency) {
                    ForEach(Currency.allCases, id: \.self) {
                        Text($0.rawValue).tag($0)
                    }
                }
            }

            Section("選填資訊") {
                Toggle("設定年利率", isOn: $hasRate.animation())
                if hasRate {
                    HStack {
                        Text("年利率")
                        Spacer()
                        TextField("0.00", value: $annualRate, format: .number)
                            .multilineTextAlignment(.trailing)
                        Text("%")
                    }
                }
                TextField("備註", text: $note)
            }
        }
        .navigationTitle(existing == nil ? "新增負債" : "編輯負債")
        .toolbar {
            ToolbarItem(placement: .cancellationAction) {
                Button("取消") { dismiss() }
            }
            ToolbarItem(placement: .confirmationAction) {
                Button("儲存") { saveAndDismiss() }
                    .disabled(name.trimmingCharacters(in: .whitespaces).isEmpty)
            }
        }
        .onAppear(perform: populate)
    }

    private func populate() {
        guard let l = existing else { return }
        name     = l.name
        category = l.category
        amount   = l.amount
        currency = l.currency
        note     = l.note ?? ""
        if let r = l.annualRate, r > 0 {
            hasRate    = true
            annualRate = r * 100
        }
    }

    private func saveAndDismiss() {
        let liability = Liability(
            id:         existing?.id ?? "liab_\(UUID().uuidString.prefix(8))",
            name:       name.trimmingCharacters(in: .whitespaces),
            category:   category,
            amount:     amount,
            currency:   currency,
            annualRate: hasRate && annualRate > 0 ? annualRate / 100 : nil,
            note:       note.isEmpty ? nil : note
        )
        if existing != nil {
            store.updateLiability(liability)
        } else {
            store.addLiability(liability)
        }
        dismiss()
    }
}
