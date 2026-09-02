import SwiftUI
import GRDB

struct ArchetypeHit: Identifiable, Hashable {
    let id: Int64
    let name: String
    let cartomancyType: String?
}

struct ReferenceView: View {
    @EnvironmentObject private var appModel: AppModel
    @State private var searchText = ""
    @State private var hits: [ArchetypeHit] = []

    var body: some View {
        NavigationStack {
            NocturneScreen {
                if hits.isEmpty && searchText.isEmpty {
                    ContentUnavailableView(
                        "Search card meanings",
                        systemImage: "text.magnifyingglass",
                        description: Text("Look up any card archetype across your reference sources."))
                } else {
                    List(hits) { hit in
                        NavigationLink(value: hit) {
                            VStack(alignment: .leading) {
                                Text(hit.name)
                                    .font(TJ.serifFont(17))
                                    .foregroundStyle(TJ.text)
                                if let type = hit.cartomancyType {
                                    Text(type).font(.caption).foregroundStyle(TJ.textFaint)
                                }
                            }
                        }
                        .listRowBackground(TJ.panel)
                    }
                    .navigationDestination(for: ArchetypeHit.self) { hit in
                        ReferenceDetailView(archetypeId: hit.id,
                                            archetypeName: hit.name)
                    }
                }
            }
            .navigationTitle("Reference")
            .searchable(text: $searchText, prompt: "Card name…")
            .onChange(of: searchText) { _, _ in search() }
        }
    }

    private func search() {
        guard !searchText.isEmpty else { hits = []; return }
        hits = (try? appModel.database.writer.read { db in
            try Row.fetchAll(db, sql: """
                SELECT id, name, cartomancy_type FROM card_archetypes
                WHERE name LIKE ? ORDER BY name LIMIT 50
                """, arguments: ["%\(searchText)%"]).map {
                ArchetypeHit(id: $0["id"], name: $0["name"],
                             cartomancyType: $0["cartomancy_type"])
            }
        }) ?? []
    }
}
