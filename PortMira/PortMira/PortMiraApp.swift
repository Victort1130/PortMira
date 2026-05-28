import SwiftUI

@main
struct PortMiraApp: App {
    @State private var store = PortfolioStore()
    @State private var budgetStore = BudgetStore()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(store)
                .environment(budgetStore)
        }
        #if os(macOS)
        .windowStyle(.titleBar)
        .windowToolbarStyle(.unified)
        #endif
    }
}
