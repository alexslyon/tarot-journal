import SwiftUI
import GRDB

struct DeckRow: Identifiable, Hashable {
    let id: Int64
    let name: String
    let cardCount: Int
}

struct DecksView: View {
    @EnvironmentObject private var appModel: AppModel
    @State private var decks: [DeckRow] = []

    var body: some View {
        NavigationStack {
            Group {
                if decks.isEmpty {
                    ContentUnavailableView(
                        "No favorite decks",
                        systemImage: "rectangle.portrait.on.rectangle.portrait",
                        description: Text("Star decks in the Mac app's Library, then sync."))
                } else {
                    List(decks) { deck in
                        HStack {
                            Text(deck.name)
                            Spacer()
                            Text("\(deck.cardCount) cards")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                }
            }
            .navigationTitle("Decks")
        }
        .task { load() }
        .onReceive(appModel.sync.$lastSyncDate) { _ in load() }
    }

    private func load() {
        decks = (try? appModel.database.writer.read { db in
            try Row.fetchAll(db, sql: """
                SELECT d.id, d.name, COUNT(c.id) AS card_count
                FROM decks d LEFT JOIN cards c ON c.deck_id = d.id
                GROUP BY d.id ORDER BY d.name
                """).map {
                DeckRow(id: $0["id"], name: $0["name"], cardCount: $0["card_count"])
            }
        }) ?? []
    }
}
