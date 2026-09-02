import SwiftUI
import GRDB

struct DeckCard: Identifiable, Hashable {
    let id: Int64
    let name: String
}

struct DeckDetailView: View {
    let deckId: Int64
    let deckName: String

    @EnvironmentObject private var appModel: AppModel
    @State private var cards: [DeckCard] = []
    @State private var searchText = ""
    @State private var viewingCard: DeckCard?

    var filtered: [DeckCard] {
        guard !searchText.isEmpty else { return cards }
        return cards.filter {
            $0.name.lowercased().contains(searchText.lowercased())
        }
    }

    var body: some View {
        NocturneScreen {
            ScrollView {
                LazyVGrid(columns: [GridItem(.adaptive(minimum: 100), spacing: 10)],
                          spacing: 12) {
                    ForEach(filtered) { card in
                        VStack(spacing: 4) {
                            CardImageView(cardId: card.id)
                                .frame(height: 150)
                                .clipShape(RoundedRectangle(cornerRadius: 5))
                            Text(card.name)
                                .font(.caption2)
                                .foregroundStyle(TJ.text3)
                                .lineLimit(1)
                        }
                        .onTapGesture { viewingCard = card }
                    }
                }
                .padding()
            }
        }
        .navigationTitle(deckName)
        .navigationBarTitleDisplayMode(.inline)
        .searchable(text: $searchText)
        .task { load() }
        .sheet(item: $viewingCard) { card in
            CardViewerView(cardId: card.id, name: card.name)
        }
    }

    private func load() {
        cards = (try? appModel.database.writer.read { db in
            try Row.fetchAll(db, sql: """
                SELECT id, name FROM cards WHERE deck_id = ?
                ORDER BY card_order, id
                """, arguments: [deckId]).map {
                DeckCard(id: $0["id"], name: $0["name"])
            }
        }) ?? []
    }
}
