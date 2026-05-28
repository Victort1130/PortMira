import SwiftUI

@main
struct PortMiraApp: App {
    @State private var store = PortfolioStore()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(store)
        }
        #if os(macOS)
        .windowStyle(.titleBar)
        .windowToolbarStyle(.unified)
        #endif
    }
}
