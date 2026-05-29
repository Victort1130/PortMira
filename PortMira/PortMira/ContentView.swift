import SwiftUI

enum AppSection: String, CaseIterable, Identifiable {
    case dashboard = "總覽"
    case holdings  = "持倉明細"
    case rebalance = "再平衡"
    case scenario  = "情境分析"
    case edit      = "編輯組合"
    case budget    = "預算追蹤"
    case backtest  = "回測工具"
    case news      = "財經新聞"

    var id: String { rawValue }

    var icon: String {
        switch self {
        case .dashboard: return "chart.pie.fill"
        case .holdings:  return "list.bullet.rectangle"
        case .rebalance: return "scale.3d"
        case .scenario:  return "wand.and.stars"
        case .edit:      return "pencil"
        case .budget:    return "creditcard"
        case .backtest:  return "chart.xyaxis.line"
        case .news:      return "newspaper"
        }
    }
}

struct ContentView: View {
    @Environment(PortfolioStore.self) private var store
    @Environment(BudgetStore.self) private var budgetStore
    @State private var selection: AppSection? = .dashboard

    var body: some View {
        NavigationSplitView {
            List(AppSection.allCases, selection: $selection) { section in
                Label(section.rawValue, systemImage: section.icon)
                    .tag(section)
            }
            .navigationTitle("PortMira")
        } detail: {
            NavigationStack {
                switch selection {
                case .dashboard, .none:
                    DashboardView()
                case .holdings:
                    HoldingsView()
                case .rebalance:
                    RebalanceView()
                case .scenario:
                    ScenarioView()
                case .edit:
                    EditPortfolioView()
                case .budget:
                    BudgetView()
                        .environment(budgetStore)
                case .backtest:
                    BacktestView()
                case .news:
                    NewsView()
                }
            }
        }
    }
}

#Preview {
    ContentView()
        .environment(PortfolioStore())
        .environment(BudgetStore())
}
