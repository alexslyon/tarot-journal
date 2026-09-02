import SwiftUI
import GRDB

/// The phone's card page: image up top (tap for the full-screen
/// zoomable view), then the card's own notes and custom fields, then
/// every reference source's texts for its archetype — mirroring the
/// desktop's card view.
struct CardInfoView: View {
    let cardId: Int64?
    let fallbackName: String?
    var reversed = false

    @EnvironmentObject private var appModel: AppModel
    @Environment(\.dismiss) private var dismiss

    @State private var name: String?
    @State private var deckName: String?
    @State private var archetype: String?
    @State private var rank: String?
    @State private var suit: String?
    @State private var notes: String?
    @State private var customFields: [(name: String, value: String)] = []
    @State private var archetypeId: Int64?
    @State private var showingImage = false

    var body: some View {
        NavigationStack {
            NocturneScreen {
                ScrollView {
                    VStack(alignment: .leading, spacing: 14) {
                        imageHeader
                        identityRow
                        if let notes, !HTMLText.strippedPlainText(notes).isEmpty {
                            panel("Notes") { HTMLText(html: notes) }
                        }
                        ForEach(customFields, id: \.name) { field in
                            panel(field.name) { HTMLText(html: field.value) }
                        }
                        if let archetypeId {
                            ArchetypeSourceTexts(archetypeId: archetypeId)
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
                .frame(height: 260)
                .clipShape(RoundedRectangle(cornerRadius: 8))
                .onTapGesture { showingImage = true }
            Spacer()
        }
    }

    /// "Seven of Wands" for pips; majors just say "Major Arcana" —
    /// "0 of Major Arcana" is nobody's phrasing.
    private var rankSuitText: String? {
        guard let suit, !suit.isEmpty else { return rank }
        if suit.localizedCaseInsensitiveContains("arcana") { return suit }
        guard let rank, !rank.isEmpty else { return suit }
        return "\(rank) of \(suit)"
    }

    @ViewBuilder
    private var identityRow: some View {
        let parts = [deckName, archetype, rankSuitText]
            .compactMap { $0 }
            .filter { !$0.isEmpty }
        if !parts.isEmpty {
            Text(parts.joined(separator: " · "))
                .font(.caption)
                .foregroundStyle(TJ.textMuted)
                .frame(maxWidth: .infinity, alignment: .center)
        }
    }

    private func panel(_ heading: String,
                       @ViewBuilder content: () -> some View) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(heading)
                .font(.caption)
                .textCase(.uppercase)
                .foregroundStyle(TJ.textMuted)
            content()
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .background(RoundedRectangle(cornerRadius: 10).fill(TJ.panel))
    }

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
            // Resolve the archetype for reference texts. Names are
            // matched as-is; when several types share a name, prefer
            // the archetype that actually has source texts.
            if let archetypeName {
                archetypeId = try Int64.fetchOne(db, sql: """
                    SELECT ca.id FROM card_archetypes ca
                    LEFT JOIN source_entries se ON se.archetype_id = ca.id
                    WHERE ca.name = ? COLLATE NOCASE
                    GROUP BY ca.id ORDER BY COUNT(se.id) DESC LIMIT 1
                    """, arguments: [archetypeName])
            }
        }
    }
}
