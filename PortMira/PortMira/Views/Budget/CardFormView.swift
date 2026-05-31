import SwiftUI

// MARK: - Card Management

struct CardManagementView: View {
    @Environment(BudgetStore.self) var budgetStore
    @Environment(PortfolioStore.self) var portfolioStore
    @Environment(\.dismiss) var dismiss

    @State private var editingCard: PaymentCard? = nil
    @State private var isAdding              = false

    var body: some View {
        if isAdding || editingCard != nil {
            CardFormView(
                editing: editingCard,
                onDone: { isAdding = false; editingCard = nil }
            )
            .environment(budgetStore)
            .environment(portfolioStore)
        } else {
            cardListView
        }
    }

    // MARK: List page (plain VStack, no NavigationStack)

    private var cardListView: some View {
        VStack(spacing: 0) {
            // Header bar
            HStack {
                Text("我的卡片").font(.title3.weight(.semibold))
                Spacer()
                Button {
                    isAdding = true
                } label: {
                    Label("新增", systemImage: "plus")
                }
                .buttonStyle(.bordered)
                .controlSize(.small)
                Button("完成") { dismiss() }
                    .buttonStyle(.borderedProminent)
                    .controlSize(.small)
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
            Divider()

            // Card list
            if budgetStore.cards.isEmpty {
                Spacer()
                VStack(spacing: 8) {
                    Image(systemName: "creditcard")
                        .font(.system(size: 36))
                        .foregroundStyle(.secondary)
                    Text("尚無卡片").font(.headline)
                    Text("點擊「新增」加入信用卡或金融卡")
                        .font(.subheadline).foregroundStyle(.secondary)
                }
                Spacer()
            } else {
                List {
                    ForEach(budgetStore.cards) { card in
                        CardRow(card: card)
                            .contentShape(Rectangle())
                            .onTapGesture { editingCard = card }
                    }
                    .onDelete { offsets in
                        offsets.forEach {
                            budgetStore.deleteCard(id: budgetStore.cards[$0].id)
                        }
                    }
                }
                .listStyle(.plain)
            }
        }
        .frame(minWidth: 400, minHeight: 360)
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

// MARK: - Card Form (plain VStack, no NavigationStack)

struct CardFormView: View {
    @Environment(BudgetStore.self) var budgetStore
    @Environment(PortfolioStore.self) var portfolioStore

    var editing: PaymentCard? = nil
    var onDone:  () -> Void  = {}

    @State private var cardName:          String      = ""
    @State private var bank:              String      = ""
    @State private var network:           CardNetwork = .visa
    @State private var cardTier:          String      = ""
    @State private var lastFour:          String      = ""
    @State private var cardType:          CardType    = .credit
    @State private var linkedLiabilityId: String?     = nil
    @State private var isDefault:         Bool        = false

    private var isEditing: Bool { editing != nil }
    private var canSave:   Bool { !cardName.isEmpty && !bank.isEmpty && lastFour.count == 4 }

    private var creditCardLiabilities: [Liability] {
        portfolioStore.portfolio.liabilities.filter { $0.category == .creditCard }
    }

    var body: some View {
        VStack(spacing: 0) {
            // Header bar
            HStack {
                Button("取消") { onDone() }
                Spacer()
                Text(isEditing ? "編輯卡片" : "新增卡片").font(.headline)
                Spacer()
                Button("儲存") { save() }
                    .buttonStyle(.borderedProminent)
                    .controlSize(.small)
                    .disabled(!canSave)
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
            Divider()

            // Form content
            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    formSection("卡片資訊") {
                        row("卡名") {
                            TextField("如 現金回饋卡", text: $cardName)
                                .textFieldStyle(.roundedBorder)
                        }
                        row("銀行") {
                            TextField("如 國泰世華", text: $bank)
                                .textFieldStyle(.roundedBorder)
                        }
                        row("發卡組織") {
                            Picker("", selection: $network) {
                                ForEach(CardNetwork.allCases) { n in
                                    Label(n.rawValue, systemImage: n.icon).tag(n)
                                }
                            }
                            .labelsHidden()
                            .frame(maxWidth: .infinity, alignment: .trailing)
                        }
                        row("卡等") {
                            TextField("如 Platinum、World（選填）", text: $cardTier)
                                .textFieldStyle(.roundedBorder)
                        }
                        row("末四碼") {
                            TextField("1234", text: $lastFour)
                                .textFieldStyle(.roundedBorder)
                                .frame(width: 70)
                                .multilineTextAlignment(.trailing)
                                .onChange(of: lastFour) { _, new in
                                    lastFour = String(new.filter(\.isNumber).prefix(4))
                                }
                        }
                        row("類型") {
                            Picker("", selection: $cardType) {
                                ForEach(CardType.allCases) { t in Text(t.displayName).tag(t) }
                            }
                            .labelsHidden()
                            .frame(maxWidth: .infinity, alignment: .trailing)
                        }
                    }

                    formSection("連結負債（選填）") {
                        Picker("關聯信用卡帳單", selection: $linkedLiabilityId) {
                            Text("不連結").tag(nil as String?)
                            ForEach(creditCardLiabilities) { l in
                                Text(l.name).tag(l.id as String?)
                            }
                        }
                        .padding(.vertical, 4)
                        if creditCardLiabilities.isEmpty {
                            Text("可在「編輯組合」新增信用卡負債後連結")
                                .font(.caption).foregroundStyle(.secondary)
                                .padding(.top, 2)
                        }
                    }

                    formSection("其他") {
                        Toggle("設為預設付款方式", isOn: $isDefault)
                            .padding(.vertical, 4)
                    }
                }
                .padding(16)
            }
        }
        .frame(minWidth: 400, minHeight: 460)
        .onAppear { prefill() }
    }

    // MARK: Layout helpers

    @ViewBuilder
    private func formSection<Content: View>(_ title: String, @ViewBuilder content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(.secondary)
                .padding(.top, 8)
            VStack(spacing: 6) { content() }
                .padding(12)
                .background(.background.secondary)
                .clipShape(RoundedRectangle(cornerRadius: 8))
        }
        .padding(.bottom, 4)
    }

    @ViewBuilder
    private func row<Content: View>(_ label: String, @ViewBuilder content: () -> Content) -> some View {
        HStack {
            Text(label)
                .frame(width: 72, alignment: .leading)
                .foregroundStyle(.secondary)
            content()
        }
    }

    // MARK: Logic

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
        onDone()
    }
}
