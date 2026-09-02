import SwiftUI
import GRDB

// MARK: - Categories

/// The non-card halves of the Reference section, mirroring the
/// desktop's tabs. Raw values are the entity kinds in the synced
/// catalog; combinations are their own thing.
enum ReferenceCategory: String, CaseIterable, Identifiable, Hashable {
    case combinations
    case sign, planet, sephira, path, chakra, number, suit, rank

    var id: String { rawValue }

    var label: String {
        switch self {
        case .combinations: return "Combinations"
        case .sign: return "Signs"
        case .planet: return "Planets"
        case .sephira: return "Sephiroth"
        case .path: return "Paths"
        case .chakra: return "Chakras"
        case .number: return "Numerology"
        case .suit: return "Suits"
        case .rank: return "Ranks"
        }
    }

    var icon: String {
        switch self {
        case .combinations: return "rectangle.on.rectangle"
        case .sign: return "sparkles"
        case .planet: return "circle.circle"
        case .sephira: return "point.3.connected.trianglepath.dotted"
        case .path: return "arrow.triangle.branch"
        case .chakra: return "circle.grid.3x3"
        case .number: return "number"
        case .suit: return "suit.club"
        case .rank: return "crown"
        }
    }
}

/// Top-level rows on the Reference front page. Groups bundle
/// related categories behind one row with a segmented switcher.
enum ReferenceGroup: String, CaseIterable, Identifiable, Hashable {
    case combinations
    case astrology
    case kabbalah
    case numbersAndSuits
    case chakras

    var id: String { rawValue }

    var label: String {
        switch self {
        case .combinations: return "Combinations"
        case .astrology: return "Astrology"
        case .kabbalah: return "Kabbalah"
        case .numbersAndSuits: return "Numbers and Suits"
        case .chakras: return "Chakras"
        }
    }

    var icon: String {
        switch self {
        case .combinations: return "rectangle.on.rectangle"
        case .astrology: return "sparkles"
        case .kabbalah: return "point.3.connected.trianglepath.dotted"
        case .numbersAndSuits: return "number"
        case .chakras: return "circle.grid.3x3"
        }
    }

    /// The entity categories inside this group (empty for
    /// combinations, which has its own screen).
    var categories: [ReferenceCategory] {
        switch self {
        case .combinations: return []
        case .astrology: return [.sign, .planet]
        case .kabbalah: return [.sephira, .path]
        case .numbersAndSuits: return [.number, .suit, .rank]
        case .chakras: return [.chakra]
        }
    }
}

/// A group's page: one category shows plainly; several get a
/// segmented switcher.
struct ReferenceGroupView: View {
    let group: ReferenceGroup
    @State private var selected: ReferenceCategory

    init(group: ReferenceGroup) {
        self.group = group
        _selected = State(initialValue: group.categories.first ?? .chakra)
    }

    var body: some View {
        NocturneScreen {
            VStack(spacing: 0) {
                if group.categories.count > 1 {
                    Picker("Section", selection: $selected) {
                        ForEach(group.categories) { category in
                            Text(category.label).tag(category)
                        }
                    }
                    .pickerStyle(.segmented)
                    .padding(.horizontal)
                    .padding(.top, 8)
                }
                EntityListView(category: selected)
                    .id(selected)
            }
        }
        .navigationTitle(group.label)
        .navigationBarTitleDisplayMode(.inline)
    }
}

struct ReferenceEntity: Identifiable, Hashable {
    let id: Int64
    let kind: String
    let key: String
    let name: String
    let subtitle: String?
    let cartomancyType: String?
}

// MARK: - Entity list

struct EntityListView: View {
    let category: ReferenceCategory

    @EnvironmentObject private var appModel: AppModel
    @State private var entities: [ReferenceEntity] = []
    @State private var searchText = ""

    var filtered: [ReferenceEntity] {
        guard !searchText.isEmpty else { return entities }
        let q = searchText.lowercased()
        return entities.filter {
            $0.name.lowercased().contains(q)
                || ($0.cartomancyType ?? "").lowercased().contains(q)
        }
    }

    var body: some View {
        List(filtered) { entity in
            NavigationLink(value: entity) {
                VStack(alignment: .leading, spacing: 2) {
                    Text(entity.name)
                        .font(TJ.serifFont(17))
                        .foregroundStyle(TJ.text)
                    if let subtitle = entity.subtitle, !subtitle.isEmpty {
                        Text(subtitle)
                            .font(.caption)
                            .foregroundStyle(TJ.textFaint)
                    }
                }
            }
            .listRowBackground(TJ.panel)
        }
        .scrollContentBackground(.hidden)
        .searchable(text: $searchText)
        .task { load() }
    }

    private func load() {
        entities = (try? appModel.database.writer.read { db in
            try Row.fetchAll(db, sql: """
                SELECT * FROM reference_entities WHERE kind = ?
                ORDER BY sort
                """, arguments: [category.rawValue]).map {
                ReferenceEntity(id: $0["id"], kind: $0["kind"],
                                key: $0["key"], name: $0["name"],
                                subtitle: $0["subtitle"],
                                cartomancyType: $0["cartomancy_type"])
            }
        }) ?? []
    }
}

// MARK: - Entity detail (source notes)

struct EntityDetailView: View {
    let entity: ReferenceEntity

    @EnvironmentObject private var appModel: AppModel
    @State private var notes: [(id: Int64, sourceName: String, content: String)] = []
    @State private var loaded = false

    var body: some View {
        NocturneScreen {
            ScrollView {
                VStack(alignment: .leading, spacing: 14) {
                    if let subtitle = entity.subtitle, !subtitle.isEmpty {
                        Text(subtitle)
                            .font(.subheadline)
                            .foregroundStyle(TJ.textMuted)
                    }
                    if loaded && notes.isEmpty {
                        ContentUnavailableView(
                            "No reference text",
                            systemImage: "text.book.closed",
                            description: Text("No source has notes for this yet — import some with the Scribe on the Mac."))
                            .padding(.top, 40)
                    }
                    ForEach(notes, id: \.id) { note in
                        VStack(alignment: .leading, spacing: 8) {
                            Text(note.sourceName)
                                .font(TJ.serifFont(17))
                                .foregroundStyle(TJ.text2)
                            HTMLText(html: note.content)
                        }
                        .padding(12)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(RoundedRectangle(cornerRadius: 10).fill(TJ.panel))
                    }
                }
                .padding()
            }
        }
        .navigationTitle(entity.name)
        .navigationBarTitleDisplayMode(.inline)
        .task { load() }
    }

    private func load() {
        notes = (try? appModel.database.writer.read { db in
            try Row.fetchAll(db, sql: """
                SELECT n.id, n.content, rs.name AS source_name
                FROM entity_source_notes n
                LEFT JOIN reference_sources rs ON rs.id = n.source_id
                WHERE n.entity_kind = ? AND n.entity_key = ?
                ORDER BY rs.name
                """, arguments: [entity.kind, entity.key]).map {
                ($0["id"], $0["source_name"] ?? "Source", $0["content"] ?? "")
            }
        }) ?? []
        loaded = true
    }
}

// MARK: - Combinations

struct CombinationRow: Identifiable {
    let id: Int64
    let title: String            // "Il Bambino + La Lettera (rev)"
    let cartomancyType: String?
    let meanings: [(id: Int64, sourceName: String, text: String)]
}

struct CombinationsView: View {
    @EnvironmentObject private var appModel: AppModel
    @State private var searchText = ""
    @State private var combos: [CombinationRow] = []

    var body: some View {
        NocturneScreen {
            Group {
                if searchText.isEmpty {
                    ContentUnavailableView(
                        "Search combinations",
                        systemImage: "rectangle.on.rectangle",
                        description: Text("Type a card name to find its combination meanings."))
                } else {
                    List(combos) { combo in
                        VStack(alignment: .leading, spacing: 6) {
                            HStack {
                                Text(combo.title)
                                    .font(TJ.serifFont(17))
                                    .foregroundStyle(TJ.text)
                                Spacer()
                                if let type = combo.cartomancyType {
                                    Text(type)
                                        .font(.caption2)
                                        .foregroundStyle(TJ.textFaint)
                                }
                            }
                            ForEach(combo.meanings, id: \.id) { meaning in
                                VStack(alignment: .leading, spacing: 2) {
                                    Text(meaning.sourceName)
                                        .font(.caption)
                                        .textCase(.uppercase)
                                        .foregroundStyle(TJ.textMuted)
                                    HTMLText(html: meaning.text)
                                }
                            }
                        }
                        .padding(.vertical, 4)
                        .listRowBackground(TJ.panel)
                    }
                }
            }
        }
        .navigationTitle("Combinations")
        .navigationBarTitleDisplayMode(.inline)
        .searchable(text: $searchText, prompt: "Card name…")
        .onChange(of: searchText) { _, _ in search() }
    }

    private func search() {
        guard !searchText.isEmpty else { combos = []; return }
        combos = (try? appModel.database.writer.read { db in
            let rows = try Row.fetchAll(db, sql: """
                SELECT c.id, c.cartomancy_type,
                       a1.name AS n1, c.archetype_1_reversed AS r1,
                       a2.name AS n2, c.archetype_2_reversed AS r2,
                       a3.name AS n3, c.archetype_3_reversed AS r3
                FROM archetype_combinations c
                JOIN card_archetypes a1 ON a1.id = c.archetype_1_id
                JOIN card_archetypes a2 ON a2.id = c.archetype_2_id
                LEFT JOIN card_archetypes a3 ON a3.id = c.archetype_3_id
                WHERE a1.name LIKE ? OR a2.name LIKE ? OR a3.name LIKE ?
                ORDER BY a1.name, a2.name LIMIT 100
                """, arguments: StatementArguments(
                    Array(repeating: "%\(searchText)%", count: 3)))
            return try rows.map { row -> CombinationRow in
                let comboId: Int64 = row["id"]
                func part(_ name: String?, _ reversed: Int?) -> String? {
                    guard let name else { return nil }
                    return reversed == 1 ? "\(name) (rev)" : name
                }
                let title = [part(row["n1"], row["r1"]),
                             part(row["n2"], row["r2"]),
                             part(row["n3"], row["r3"])]
                    .compactMap { $0 }
                    .joined(separator: " + ")
                let meanings = try Row.fetchAll(db, sql: """
                    SELECT m.id, m.meaning, rs.name AS source_name
                    FROM combination_meanings m
                    LEFT JOIN reference_sources rs ON rs.id = m.source_id
                    WHERE m.combination_id = ? ORDER BY m.sort_order
                    """, arguments: [comboId]).map { row ->
                        (id: Int64, sourceName: String, text: String) in
                    (id: row["id"],
                     sourceName: row["source_name"] ?? "Source",
                     text: row["meaning"] ?? "")
                }
                return CombinationRow(id: comboId, title: title,
                                      cartomancyType: row["cartomancy_type"],
                                      meanings: meanings)
            }
        }) ?? []
    }
}
