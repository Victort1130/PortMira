import SwiftUI

// MARK: - Card Management (list + navigation host)

struct CardManagementView: View {
    @Environment(BudgetStore.self) var budgetStore
    @Environment(PortfolioStore.self) var portfolioStore
    @Environment(\.dismiss) var dismiss

    @State private var editingCard: PaymentCard? = nil

    var body: some View {
        NavigationStack {
            List {
                if budgetStore.cards.isEmpty {
                    ContentUnavailableView(
                        "尚無卡片",
                        systemImage: "creditcard",
                        description: Text("點擊右上角「＋」新增信用卡或金融卡")
                    )
                }
                ForEach(budgetStore.cards) { card in
                    CardRow(card: card)
                        .contentShape(Rectangle())
                        .onTapGesture { editingCard = card }
                }
                .onDelete { offsets in
                    offsets.forEach { budgetStore.deleteCard(id: budgetStore.cards[$0].id) }
                }
            }
            .navigationTitle("我的卡片")
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("完成") { dismiss() }
                }
                ToolbarItem {
                    NavigationLink {
                        CardFormView()
                            .environment(budgetStore)
                            .environment(portfolioStore)
                    } label: {
                        Label("新增", systemImage: "plus")
                    }
                }
            }
            .navigationDestination(item: $editingCard) { card in
                CardFormView(editing: card)
                    .environment(budgetStore)
                    .environment(portfolioStore)
            }
        }
        .frame(minWidth: 460, minHeight: 420)
    }
}

// MARK: - Card Row

private struct CardRow: View {
    let card: PaymentCard

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: card.network.icon)
                .font(.title2)
                .foregroundStyle(.secondary)
                .frame(width: 32)
            VStack(alignment: .leading, spacing: 3) {
                HStack(spacing: 6) {
                    Text(card.cardName).font(.subheadline.weight(.semibold))
                    if card.isDefault {
                        Text("預設")
                            .font(.caption2)
                            .padding(.horizontal, 5).padding(.vertical, 2)
                            .background(.blue.opacity(0.12))
                            .foregroundStyle(.blue)
                            .clipShape(RoundedRectangle(cornerRadius: 4))
                    }
                }
                Text([card.bank,
                      card.cardType.displayName,
                      card.network.rawValue,
                      card.cardTier.isEmpty ? nil : card.cardTier]
                    .compactMap { $0 }
                    .joined(separator: " · "))
                    .font(.caption).foregroundStyle(.secondary)
                Text("···· \(card.lastFour)").font(.caption).foregroundStyle(.secondary)
            }
        }
        .padding(.vertical, 2)
    }
}

// MARK: - Card Form (embedded in CardManagementView's NavigationStack)

struct CardFormView: View {
    @Environment(BudgetStore.self) var budgetStore
    @Environment(PortfolioStore.self) var portfolioStore
    @Environment(\.dismiss) var dismiss

    var editing: PaymentCard? = nil

    @State private var cardName:          String      = ""
    @State private var bank:              String      = ""
    @State private var network:           CardNetwork = .visa
    @State private var cardTier:          String      = ""
    @State private var lastFour:          String      = ""
    @State private var cardType:          CardType    = .credit
    @State private var linkedLiabilityId: String?     = nil
    @State private var isDefault:         Bool        = false

    private var isEditing: Bool { editing != nil }

    private var creditCardLiabilities: [Liability] {
        portfolioStore.portfolio.liabilities.filter { $0.category == .creditCard }
    }

    var body: some View {
        Form {
            Section("卡片資訊") {
                TextField("卡名（如 現金回饋卡）", text: $cardName)
                TextField("銀行（如 國泰世華）", text: $bank)

                Picker("發卡組織", selection: $network) {
                    ForEach(CardNetwork.allCases) { n in
                        Label(n.rawValue, systemImage: n.icon).tag(n)
                    }
                }

                TextField("卡等（如 Platinum、World）", text: $cardTier)

                HStack {
                    Text("末四碼")
                    Spacer()
                    TextField("1234", text: $lastFour)
                        .multilineTextAlignment(.trailing)
                        .frame(width: 60)
                        .onChange(of: lastFour) { _, new in
                            lastFour = String(new.filter(\.isNumber).prefix(4))
                        }
                }

                Picker("類型", selection: $cardType) {
                    ForEach(CardType.allCases) { t in Text(t.displayName).tag(t) }
                }
            }

            Section("連結負債（選填）") {
                Picker("關聯信用卡帳單", selection: $linkedLiabilityId) {
                    Text("不連結").tag(nil as String?)
                    ForEach(creditCardLiabilities) { l in
                        Text(l.name).tag(l.id as String?)
                    }
                }
                if creditCardLiabilities.isEmpty {
                    Text("可在「編輯組合」新增信用卡負債後連結")
                        .font(.caption).foregroundStyle(.secondary)
                }
            }

            Section {
                Toggle("設為預設付款方式", isOn: $isDefault)
            }
        }
        .navigationTitle(isEditing ? "編輯卡片" : "新增卡片")
        .toolbar {
            ToolbarItem(placement: .confirmationAction) {
                Button("儲存") { save() }
                    .disabled(cardName.isEmpty || bank.isEmpty || lastFour.count != 4)
            }
        }
        .onAppear { prefill() }
    }

    private func prefill() {
        guard let c = editing else { return }
        cardName          = c.cardName
        bank              = c.bank
        network           = c.network
        cardTier          = c.cardTier
        lastFour          = c.lastFour
        cardType          = c.cardType
        linkedLiabilityId = c.linkedLiabilityId
        isDefault         = c.isDefault
    }

    private func save() {
        let card = PaymentCard(
            id:                editing?.id ?? "card_\(UUID().uuidString.prefix(8))",
            cardName:          cardName,
            bank:              bank,
            network:           network,
            cardTier:          cardTier,
            lastFour:          lastFour,
            cardType:          cardType,
            linkedLiabilityId: linkedLiabilityId,
            isDefault:         isDefault
        )
        if isEditing { budgetStore.updateCard(card) }
        else         { budgetStore.addCard(card) }
        dismiss()
    }
}
