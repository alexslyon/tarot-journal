import SwiftUI
import GRDB

/// The phone's card page: image up top (tap for the full-screen
/// zoomable view), then three tabs — Classification (deck, archetype,
/// rank, suit, card notes), Correspondences (per-system assignments
/// for the card's archetype), and Custom Fields (the deck's own
/// fields) — plus a link into the Reference page for the archetype's
/// source texts.
struct CardInfoView: View {
    let cardId: Int64?
    let fallbackName: String?
    var reversed = false

    enum Tab: String, CaseIterable, Identifiable {
        case classification = "Classification"
        case correspondences = "Correspondences"
        case fields = "Custom Fields"
        var id: String { rawValue }
    }

    struct SystemAssignments: Identifiable {
        let id: Int64
        let name: String
        let values: [(field: String, value: String)]
    }

    @EnvironmentObject private var appModel: AppModel
    @Environment(\.dismiss) private var dismiss

    @State private var tab: Tab = {
        #if DEBUG
        let args = ProcessInfo.processInfo.arguments
        if let i = args.firstIndex(of: "-cardTab"), i + 1 < args.count,
           let t = Tab.allCases.first(where: { $0.rawValue.lowercased().hasPrefix(args[i + 1].lowercased()) }) {
            return t
        }
        #endif
        return .classification
    }()
    @State private var name: String?
    @State private var deckName: String?
    @State private var archetype: String?
    @State private var rank: String?
    @State private var suit: String?
    @State private var cardType: String?
    @State private var notes: String?
    @State private var customFields: [(name: String, value: String)] = []
    @State private var systems: [SystemAssignments] = []
    @State private var archetypeId: Int64?
    @State private var showingImage = false

    var body: some View {
        NavigationStack {
            NocturneScreen {
                ScrollView {
                    VStack(alignment: .leading, spacing: 14) {
                        imageHeader

                        Picker("Section", selection: $tab) {
                            ForEach(Tab.allCases) { t in
                                Text(t.rawValue).tag(t)
                            }
                        }
                        .pickerStyle(.segmented)

                        switch tab {
                        case .classification: classificationTab
                        case .correspondences: correspondencesTab
                        case .fields: fieldsTab
                        }

                        if let archetypeId {
                            NavigationLink {
                                ReferenceDetailView(
                                    archetypeId: archetypeId,
                                    archetypeName: archetype ?? name ?? "Archetype")
                            } label: {
                                HStack {
                                    Image(systemName: "text.book.closed")
                                    Text("Reference notes for \(archetype ?? name ?? "this card")")
                                    Spacer()
                                    Image(systemName: "chevron.right")
                                        .font(.caption)
                                        .foregroundStyle(TJ.textMuted)
                                }
                                .foregroundStyle(TJ.textAccent)
                                .padding(12)
                                .background(RoundedRectangle(cornerRadius: 10).fill(TJ.tint))
                            }
                        }
                    }
                    .padding()
                }
            }
            .navigationTitle((name ?? fallbackName ?? "Card")
                             + (reversed ? " (reversed)" : ""))
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") { dismiss() }
                }
            }
        }
        .preferredColorScheme(.dark)
        .task { load() }
        .sheet(isPresented: $showingImage) {
            CardViewerView(cardId: cardId, name: name ?? fallbackName,
                           reversed: reversed)
        }
    }

    private var imageHeader: some View {
        HStack {
            Spacer()
            CardImageView(cardId: cardId, reversed: reversed)
                .frame(height: 240)
                .clipShape(RoundedRectangle(cornerRadius: 8))
                .onTapGesture { showingImage = true }
            Spacer()
        }
    }

    // MARK: - Tabs

    @ViewBuilder
    private var classificationTab: some View {
        panel {
            infoRow("Deck", deckName)
            infoRow("Archetype", archetype)
            infoRow("Rank", rank)
            infoRow("Suit", suit)
            infoRow("Type", cardType)
        }
        if let notes, !HTMLText.strippedPlainText(notes).isEmpty {
            titledPanel("Card notes") { HTMLText(html: notes) }
        }
    }

    @ViewBuilder
    private var correspondencesTab: some View {
        if systems.isEmpty {
            emptyNote("No correspondence system covers this card yet. Systems are managed on the Mac in Settings → Correspondences.")
        }
        ForEach(systems) { system in
            titledPanel(system.name) {
                VStack(alignment: .leading, spacing: 6) {
                    ForEach(system.values, id: \.field) { pair in
                        infoRow(pair.field.replacingOccurrences(of: "_", with: " ").capitalized, pair.value)
                    }
                }
            }
        }
    }

    @ViewBuilder
    private var fieldsTab: some View {
        if customFields.isEmpty {
            emptyNote("This deck has no custom fields filled in for this card.")
        }
        ForEach(customFields, id: \.name) { field in
            titledPanel(field.name) { HTMLText(html: field.value) }
        }
    }

    // MARK: - Pieces

    private func infoRow(_ label: String, _ value: String?) -> some View {
        Group {
            if let value, !value.isEmpty {
                HStack(alignment: .firstTextBaseline) {
                    Text(label)
                        .font(.caption)
                        .foregroundStyle(TJ.textMuted)
                        .frame(width: 92, alignment: .leading)
                    Text(value)
                        .font(.callout)
                        .foregroundStyle(TJ.text)
                    Spacer(minLength: 0)
                }
            }
        }
    }

    private func panel(@ViewBuilder content: () -> some View) -> some View {
        VStack(alignment: .leading, spacing: 8) { content() }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(12)
            .background(RoundedRectangle(cornerRadius: 10).fill(TJ.panel))
    }

    private func titledPanel(_ heading: String,
                             @ViewBuilder content: () -> some View) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(heading)
                .font(TJ.serifFont(16))
                .foregroundStyle(TJ.text2)
            content()
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .background(RoundedRectangle(cornerRadius: 10).fill(TJ.panel))
    }

    private func emptyNote(_ text: String) -> some View {
        Text(text)
            .font(.caption)
            .foregroundStyle(TJ.textFaint)
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(12)
            .background(RoundedRectangle(cornerRadius: 10).fill(TJ.panel))
    }

    // MARK: - Data

    private func load() {
        try? appModel.database.writer.read { db in
            var archetypeName: String? = fallbackName
            if let cardId,
               let row = try Row.fetchOne(db, sql: """
                   SELECT c.name, c.archetype, c.rank, c.suit, c.notes,
                          c.custom_fields, d.name AS deck_name
                   FROM cards c LEFT JOIN decks d ON d.id = c.deck_id
                   WHERE c.id = ?
                   """, arguments: [cardId]) {
                name = row["name"]
                archetype = row["archetype"]
                rank = row["rank"]
                suit = row["suit"]
                notes = row["notes"]
                deckName = row["deck_name"]
                archetypeName = archetype ?? name
                if let raw: String = row["custom_fields"],
                   let data = raw.data(using: .utf8),
                   let dict = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
                    customFields = dict
                        .compactMap { key, value in
                            let text = value as? String ?? ""
                            return text.isEmpty ? nil : (key, text)
                        }
                        .sorted { $0.0 < $1.0 }
                }
            }
            // Resolve the archetype (for correspondences and the
            // reference link). Names are matched as-is; when several
            // types share a name, prefer the one with source texts.
            if let archetypeName {
                if let row = try Row.fetchOne(db, sql: """
                    SELECT ca.id, ca.cartomancy_type FROM card_archetypes ca
                    LEFT JOIN source_entries se ON se.archetype_id = ca.id
                    WHERE ca.name = ? COLLATE NOCASE
                    GROUP BY ca.id ORDER BY COUNT(se.id) DESC LIMIT 1
                    """, arguments: [archetypeName]) {
                    archetypeId = row["id"]
                    cardType = row["cartomancy_type"]
                }
            }
            if let archetypeId {
                let rows = try Row.fetchAll(db, sql: """
                    SELECT s.id AS system_id, s.name AS system_name,
                           a.field_name, a.field_value
                    FROM correspondence_assignments a
                    JOIN correspondence_systems s ON s.id = a.system_id
                    WHERE a.archetype_id = ?
                      AND a.field_value IS NOT NULL AND a.field_value != ''
                    ORDER BY s.name, a.field_name
                    """, arguments: [archetypeId])
                var bySystem: [Int64: SystemAssignments] = [:]
                var order: [Int64] = []
                for row in rows {
                    let systemId: Int64 = row["system_id"]
                    if bySystem[systemId] == nil {
                        bySystem[systemId] = SystemAssignments(
                            id: systemId, name: row["system_name"] ?? "System",
                            values: [])
                        order.append(systemId)
                    }
                    bySystem[systemId] = SystemAssignments(
                        id: systemId,
                        name: bySystem[systemId]!.name,
                        values: bySystem[systemId]!.values
                            + [(row["field_name"] ?? "", row["field_value"] ?? "")])
                }
                systems = order.compactMap { bySystem[$0] }
            }
        }
    }
}
