import SwiftUI

struct EditPortfolioView: View {
    @Environment(PortfolioStore.self) private var store
    @State private var showAddAsset     = false
    @State private var showAddLiability = false
    @State private var editingAsset:     Asset?     = nil
    @State private var editingLiability: Liability? = nil

    var body: some View {
        List {
            // ── Assets ────────────────────────────────────────────────────
            Section {
                ForEach(store.portfolio.assets) { asset in
                    Button {
                        editingAsset = asset
                    } label: {
                        HStack {
                            VStack(alignment: .leading, spacing: 2) {
                                Text(asset.name).fontWeight(.medium)
                                Text("\(asset.category.displayName)  ·  \(asset.ticker ?? "—")")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                            Spacer()
                            VStack(alignment: .trailing, spacing: 2) {
                                Text("\(asset.quantity.formatted()) × \(asset.costPerUnit.formatted(.number.precision(.fractionLength(2))))")
                                    .font(.subheadline)
                                Text(asset.currency.rawValue)
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                        }
                    }
                    .buttonStyle(.plain)
                }
                .onDelete { store.deleteAssets(at: $0) }

                Button {
                    showAddAsset = true
                } label: {
                    Label("新增資產", systemImage: "plus.circle")
                }
            } header: {
                Text("資產 Assets (\(store.portfolio.assets.count))")
            }

            // ── Liabilities ───────────────────────────────────────────────
            Section {
                ForEach(store.portfolio.liabilities) { liability in
                    Button {
                        editingLiability = liability
                    } label: {
                        HStack {
                            VStack(alignment: .leading, spacing: 2) {
                                Text(liability.name).fontWeight(.medium)
                                Text(liability.category.displayName)
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                            Spacer()
                            VStack(alignment: .trailing, spacing: 2) {
                                Text(liability.amount.formatted(.number.precision(.fractionLength(0))))
                                    .font(.subheadline)
                                Text(liability.currency.rawValue)
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                        }
                    }
                    .buttonStyle(.plain)
                }
                .onDelete { store.deleteLiabilities(at: $0) }

                Button {
                    showAddLiability = true
                } label: {
                    Label("新增負債", systemImage: "plus.circle")
                }
            } header: {
                Text("負債 Liabilities (\(store.portfolio.liabilities.count))")
            }
        }
        .navigationTitle("編輯組合")
        .sheet(isPresented: $showAddAsset) {
            NavigationStack { AssetFormView() }
        }
        .sheet(item: $editingAsset) { asset in
            NavigationStack { AssetFormView(existing: asset) }
        }
        .sheet(isPresented: $showAddLiability) {
            NavigationStack { LiabilityFormView() }
        }
        .sheet(item: $editingLiability) { liability in
            NavigationStack { LiabilityFormView(existing: liability) }
        }
    }
}
