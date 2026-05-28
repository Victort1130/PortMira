import SwiftUI

struct AssetFormView: View {
    @Environment(PortfolioStore.self) private var store
    @Environment(\.dismiss) private var dismiss

    var existing: Asset? = nil

    @State private var name:        String        = ""
    @State private var category:    AssetCategory = .stock
    @State private var ticker:      String        = ""
    @State private var quantity:    Double        = 0
    @State private var costPerUnit: Double        = 0
    @State private var currency:    Currency      = .usd
    @State private var note:        String        = ""

    @State private var hasPurchaseDate: Bool = false
    @State private var purchaseDate:    Date = Date()
    @State private var hasTargetPct:    Bool = false
    @State private var targetPct:       Double = 0

    var body: some View {
        Form {
            // ── 基本資訊 ──────────────────────────────────────────────────
            Section("基本資訊") {
                TextField("名稱", text: $name)

                Picker("類別", selection: $category) {
                    ForEach(AssetCategory.allCases, id: \.self) {
                        Text($0.displayName).tag($0)
                    }
                }

                if category.isAutoPrice {
                    TextField("Ticker（如 AAPL、2330.TW、bitcoin）", text: $ticker)
                        #if os(iOS)
                        .autocorrectionDisabled()
                        .textInputAutocapitalization(.characters)
                        #endif
                }
            }

            // ── 數量與成本 ────────────────────────────────────────────────
            Section("數量與成本") {
                HStack {
                    Text("數量")
                    Spacer()
                    TextField("0", value: $quantity, format: .number)
                        .multilineTextAlignment(.trailing)
                }
                HStack {
                    Text("每單位成本")
                    Spacer()
                    TextField("0.00", value: $costPerUnit, format: .number)
                        .multilineTextAlignment(.trailing)
                }
                Picker("幣別", selection: $currency) {
                    ForEach(Currency.allCases, id: \.self) {
                        Text($0.rawValue).tag($0)
                    }
                }
            }

            // ── 選填資訊 ──────────────────────────────────────────────────
            Section("選填資訊") {
                Toggle("設定購入日期", isOn: $hasPurchaseDate.animation())
                if hasPurchaseDate {
                    DatePicker("購入日期", selection: $purchaseDate, displayedComponents: .date)
                }

                Toggle("設定再平衡目標 %", isOn: $hasTargetPct.animation())
                if hasTargetPct {
                    HStack {
                        Text("目標比例")
                        Spacer()
                        TextField("0", value: $targetPct, format: .number)
                            .multilineTextAlignment(.trailing)
                        Text("%")
                    }
                }

                TextField("備註", text: $note)
            }
        }
        .navigationTitle(existing == nil ? "新增資產" : "編輯資產")
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

    // MARK: - Helpers

    private func populate() {
        guard let a = existing else { return }
        name        = a.name
        category    = a.category
        ticker      = a.ticker ?? ""
        quantity    = a.quantity
        costPerUnit = a.costPerUnit
        currency    = a.currency
        note        = a.note ?? ""
        if let pd = a.purchaseDate, let d = DateFormatter.yyyyMMdd.date(from: pd) {
            hasPurchaseDate = true
            purchaseDate    = d
        }
        if let tp = a.targetPct, tp > 0 {
            hasTargetPct = true
            targetPct    = tp
        }
    }

    private func saveAndDismiss() {
        let asset = Asset(
            id:           existing?.id ?? "asset_\(UUID().uuidString.prefix(8))",
            name:         name.trimmingCharacters(in: .whitespaces),
            category:     category,
            ticker:       category.isAutoPrice && !ticker.isEmpty ? ticker.uppercased() : nil,
            quantity:     quantity,
            costPerUnit:  category == .cash ? 1.0 : costPerUnit,
            currency:     currency,
            purchaseDate: hasPurchaseDate ? DateFormatter.yyyyMMdd.string(from: purchaseDate) : nil,
            targetPct:    hasTargetPct && targetPct > 0 ? targetPct : nil,
            note:         note.isEmpty ? nil : note
        )
        if existing != nil {
            store.updateAsset(asset)
        } else {
            store.addAsset(asset)
        }
        dismiss()
    }
}
