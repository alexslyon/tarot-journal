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
        #if DEBUG
        .sheet(item: .constant(DebugRoute.fromLaunchArguments())) { route in
            // Launch-argument deep links so screens can be opened from
            // `simctl launch` during development, e.g.
            //   ... com.aslyon.TarotCompanion -openEntry 323
            NavigationStack {
                switch route {
                case .entry(let id): EntryDetailView(entryId: id)
                case .deck(let id): DeckDetailView(deckId: id, deckName: "Deck")
                case .archetype(let id):
                    ReferenceDetailView(archetypeId: id, archetypeName: "Archetype")
                }
            }
            .preferredColorScheme(.dark)
        }
        #endif
    }
}

#if DEBUG
enum DebugRoute: Identifiable {
    case entry(Int64)
    case deck(Int64)
    case archetype(Int64)

    var id: String {
        switch self {
        case .entry(let id): return "entry-\(id)"
        case .deck(let id): return "deck-\(id)"
        case .archetype(let id): return "archetype-\(id)"
        }
    }

    static func fromLaunchArguments() -> DebugRoute? {
        let args = ProcessInfo.processInfo.arguments
        func value(after flag: String) -> Int64? {
            guard let index = args.firstIndex(of: flag),
                  index + 1 < args.count else { return nil }
            return Int64(args[index + 1])
        }
        if let id = value(after: "-openEntry") { return .entry(id) }
        if let id = value(after: "-openDeck") { return .deck(id) }
        if let id = value(after: "-openArchetype") { return .archetype(id) }
        return nil
    }
}
#endif

#Preview {
    ContentView()
        .environmentObject(AppModel())
}
