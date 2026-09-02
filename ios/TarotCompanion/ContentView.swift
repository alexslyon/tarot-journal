import SwiftUI

struct ContentView: View {
    var body: some View {
        TabView {
            JournalListView()
                .tabItem { Label("Journal", systemImage: "book.closed") }
            ReferenceView()
                .tabItem { Label("Reference", systemImage: "text.magnifyingglass") }
            DecksView()
                .tabItem { Label("Decks", systemImage: "rectangle.portrait.on.rectangle.portrait") }
            SettingsView()
                .tabItem { Label("Settings", systemImage: "gearshape") }
        }
    }
}

#Preview {
    ContentView()
        .environmentObject(AppModel())
}
