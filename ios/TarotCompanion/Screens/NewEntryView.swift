import SwiftUI
import GRDB

/// The quick-entry composer: querent → deck → spread → cards → notes.
/// Optimized for speed at the reading table; the entry pushes to the
/// Mac (or waits in the outbox when it's unreachable) and gets the
/// "logged on phone" tag there.
struct NewEntryView: View {
    @EnvironmentObject private var appModel: AppModel
    @Environment(\.dismiss) private var dismiss

    struct PickedCard: Identifiable, Equatable {
        let id = UUID()
        var cardId: Int64
        var name: String
        var reversed = false
    }

    struct SpreadOption: Identifiable, Hashable {
        let id: Int64
        let name: String
        let positions: [SpreadPosition]

        var positionLabels: [String] { positions.map { $0.label ?? "" } }

        static func == (lhs: SpreadOption, rhs: SpreadOption) -> Bool {
            lhs.id == rhs.id
        }
        func hash(into hasher: inout Hasher) { hasher.combine(id) }
    }

    enum ActivePicker: String, Identifiable {
        case querent, deck, spread
        var id: String { rawValue }
    }

    @State private var title = ""
    @State private var notes = ""
    @State private var querentId: Int64?
    @State private var deckId: Int64?
    @State private var spread: SpreadOption?
    @State private var readingDate = Date()
    @State private var locationName = ""
    @State private var cards: [PickedCard?] = []     // one slot per position
    @State private var freeformCards: [PickedCard] = []

    @State private var profiles: [(id: Int64, name: String)] = []
    @State private var decks: [(id: Int64, name: String)] = []
    @State private var spreads: [SpreadOption] = []
    @State private var activePicker: ActivePicker?
    @State private var pickingSlot: Int?          // which slot the card picker fills
    @State private var pickingFreeform = false
    @State private var saving = false

    private var usingSpread: Bool { spread != nil }
    private var chosenCards: [PickedCard?] { usingSpread ? cards : freeformCards }
    private var canSave: Bool {
        deckId != nil && chosenCards.contains { $0 != nil } && !saving
    }

    var body: some View {
        NavigationStack {
            NocturneScreen {
                Form {
                    Group {
                        detailsSection
                        cardsSection
                        notesSection
                    }
                    .listRowBackground(TJ.panel)
                }
            }
            .navigationTitle("New Reading")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") { Task { await save() } }
                        .disabled(!canSave)
                }
            }
            .sheet(isPresented: Binding(
                get: { pickingSlot != nil || pickingFreeform },
                set: { if !$0 { pickingSlot = nil; pickingFreeform = false } }
            )) {
                if let deckId {
                    CardPickerView(deckId: deckId) { picked in
                        place(picked)
                    }
                }
            }
            .sheet(item: $activePicker) { picker in
                optionPicker(for: picker)
            }
        }
        .task { load() }
    }

    @ViewBuilder
    private func optionPicker(for picker: ActivePicker) -> some View {
        switch picker {
        case .querent:
            OptionPickerSheet(
                title: "Querent",
                options: profiles.map { ($0.id, $0.name) },
                noneLabel: "None") { querentId = $0 }
        case .deck:
            OptionPickerSheet(
                title: "Deck",
                options: decks.map { ($0.id, $0.name) },
                noneLabel: nil) { picked in
                if let picked { deckId = picked }
            }
        case .spread:
            OptionPickerSheet(
                title: "Spread",
                options: spreads.map { ($0.id, $0.name) },
                noneLabel: "No spread") { picked in
                spread = spreads.first { $0.id == picked }
                cards = Array(repeating: nil,
                              count: spread?.positions.count ?? 0)
            }
        }
    }

    /// The picked cards shaped for the live spread preview.
    private var previewCards: [ReadingCard] {
        cards.enumerated().compactMap { index, slot in
            guard let card = slot else { return nil }
            return ReadingCard(
                name: card.name, reversed: card.reversed, deckId: deckId,
                deckName: nil, positionIndex: index, cardId: card.cardId,
                clarifies: nil)
        }
    }

    // MARK: - Sections

    private var detailsSection: some View {
        Section("Reading") {
            TextField("Title (optional)", text: $title)

            pickerRow("Querent",
                      value: profiles.first { $0.id == querentId }?.name ?? "None") {
                activePicker = .querent
            }
            pickerRow("Deck",
                      value: decks.first { $0.id == deckId }?.name ?? "Choose…") {
                activePicker = .deck
            }
            pickerRow("Spread", value: spread?.name ?? "No spread") {
                activePicker = .spread
            }

            DatePicker("Date & time", selection: $readingDate)
                .tint(TJ.accent)

            TextField("Location (optional)", text: $locationName)
                .autocorrectionDisabled()
        }
    }

    private func pickerRow(_ label: String, value: String,
                           action: @escaping () -> Void) -> some View {
        Button(action: action) {
            HStack {
                Text(label).foregroundStyle(TJ.text)
                Spacer()
                Text(value)
                    .foregroundStyle(TJ.accent)
                    .lineLimit(1)
                Image(systemName: "chevron.up.chevron.down")
                    .font(.caption2)
                    .foregroundStyle(TJ.textFaint)
            }
        }
    }

    @ViewBuilder
    private var cardsSection: some View {
        Section("Cards") {
            if deckId == nil {
                Text("Choose a deck first.")
                    .font(.caption)
                    .foregroundStyle(TJ.textFaint)
            } else if usingSpread {
                // Live spread preview: tap a slot to fill it, tap a
                // placed card to re-pick it.
                if let spread, !spread.positions.isEmpty {
                    SpreadLayoutView(
                        cards: previewCards,
                        positions: spread.positions,
                        onTapCard: { card in
                            if let index = card.positionIndex { pickingSlot = index }
                        },
                        onTapEmptySlot: { pickingSlot = $0 })
                        .padding(.vertical, 6)
                }
                ForEach(Array((spread?.positionLabels ?? []).enumerated()),
                        id: \.offset) { index, label in
                    slotRow(label: label.isEmpty ? "Position \(index + 1)" : label,
                            card: cards.indices.contains(index) ? cards[index] : nil) {
                        pickingSlot = index
                    } clear: {
                        if cards.indices.contains(index) { cards[index] = nil }
                    } toggleReversed: {
                        if cards.indices.contains(index) { cards[index]?.reversed.toggle() }
                    }
                }
            } else {
                ForEach(Array(freeformCards.enumerated()), id: \.element.id) { index, card in
                    slotRow(label: "Card \(index + 1)", card: card) {
                        // tapping re-picks this slot? keep simple: no-op
                    } clear: {
                        freeformCards.remove(at: index)
                    } toggleReversed: {
                        freeformCards[index].reversed.toggle()
                    }
                }
                Button {
                    pickingFreeform = true
                } label: {
                    Label("Add card", systemImage: "plus")
                }
            }
        }
    }

    private func slotRow(label: String, card: PickedCard?,
                         pick: @escaping () -> Void,
                         clear: @escaping () -> Void,
                         toggleReversed: @escaping () -> Void) -> some View {
        HStack {
            VStack(alignment: .leading, spacing: 2) {
                Text(label).font(.caption).foregroundStyle(TJ.textMuted)
                if let card {
                    Text(card.name + (card.reversed ? "  ⟲ reversed" : ""))
                        .foregroundStyle(TJ.text)
                } else {
                    Button("Choose card…", action: pick)
                        .foregroundStyle(TJ.accent)
                }
            }
            Spacer()
            if card != nil {
                Button(action: toggleReversed) {
                    Image(systemName: "arrow.up.arrow.down")
                }
                .buttonStyle(.borderless)
                Button(action: clear) {
                    Image(systemName: "xmark.circle")
                }
                .buttonStyle(.borderless)
                .foregroundStyle(TJ.textFaint)
            }
        }
    }

    private var notesSection: some View {
        Section("Notes") {
            TextEditor(text: $notes)
                .frame(minHeight: 110)
                .scrollContentBackground(.hidden)
        }
    }

    // MARK: - Behavior

    private func place(_ picked: PickedCard) {
        if let slot = pickingSlot {
            if cards.indices.contains(slot) { cards[slot] = picked }
            pickingSlot = nil
        } else if pickingFreeform {
            freeformCards.append(picked)
            pickingFreeform = false
        }
    }

    private func load() {
        try? appModel.database.writer.read { db in
            profiles = try Row.fetchAll(
                db, sql: "SELECT id, name FROM profiles WHERE hidden IS NOT 1 ORDER BY name")
                .map { ($0["id"], $0["name"]) }
            decks = try Row.fetchAll(
                db, sql: "SELECT id, name FROM decks ORDER BY name")
                .map { ($0["id"], $0["name"]) }
            let decoder = JSONDecoder()
            spreads = try Row.fetchAll(
                db, sql: """
                    SELECT id, name, positions FROM spreads
                    WHERE archived IS NOT 1 ORDER BY name
                    """)
                .map { row in
                    var positions: [SpreadPosition] = []
                    if let raw: String = row["positions"],
                       let data = raw.data(using: .utf8),
                       let decoded = try? decoder.decode([SpreadPosition].self, from: data) {
                        positions = decoded
                    }
                    return SpreadOption(id: row["id"], name: row["name"],
                                        positions: positions)
                }
        }
    }

    private func save() async {
        guard let deckId else { return }
        saving = true
        let deckName = decks.first { $0.id == deckId }?.name

        var cardsUsed: [[String: Any]] = []
        for (index, slot) in chosenCards.enumerated() {
            guard let card = slot else { continue }
            cardsUsed.append([
                "card_id": card.cardId,
                "name": card.name,
                "reversed": card.reversed,
                "position_index": index,
                "deck_id": deckId,
                "deck_name": deckName ?? "",
            ])
        }

        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "yyyy-MM-dd'T'HH:mm:ss"

        var payload: [String: Any] = [
            "sync_uuid": UUID().uuidString,
            "reading_datetime": formatter.string(from: readingDate),
            "querent_ids": querentId.map { [$0] } ?? [],
            "reading": [
                "deck_id": deckId,
                "spread_id": spread?.id as Any,
                "spread_name": spread?.name as Any,
                "deck_name": deckName ?? "",
                "cards_used": cardsUsed,
            ] as [String: Any],
        ]
        if !title.trimmingCharacters(in: .whitespaces).isEmpty {
            payload["title"] = title
        }
        let trimmedLocation = locationName.trimmingCharacters(in: .whitespaces)
        if !trimmedLocation.isEmpty {
            // Name only — the Mac geocodes it into coordinates on arrival.
            payload["location_name"] = trimmedLocation
        }
        let trimmedNotes = notes.trimmingCharacters(in: .whitespacesAndNewlines)
        if !trimmedNotes.isEmpty {
            payload["content"] = Self.paragraphsToHTML(trimmedNotes)
        }

        await appModel.sync.submitEntry(payload)
        saving = false
        dismiss()
    }

    /// Plain text from the phone keyboard becomes the same simple
    /// HTML the desktop's rich-text editor produces.
    static func paragraphsToHTML(_ text: String) -> String {
        text.split(separator: "\n", omittingEmptySubsequences: true)
            .map { line -> String in
                let escaped = String(line)
                    .replacingOccurrences(of: "&", with: "&amp;")
                    .replacingOccurrences(of: "<", with: "&lt;")
                    .replacingOccurrences(of: ">", with: "&gt;")
                return "<p>\(escaped)</p>"
            }
            .joined()
    }
}

// MARK: - Searchable option picker

/// A searchable list sheet standing in for a dropdown — with dozens
/// of decks and spreads, scrolling a wheel picker doesn't scale.
struct OptionPickerSheet: View {
    let title: String
    let options: [(id: Int64, label: String)]
    let noneLabel: String?
    let onPick: (Int64?) -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var searchText = ""

    var filtered: [(id: Int64, label: String)] {
        guard !searchText.isEmpty else { return options }
        return options.filter {
            $0.label.lowercased().contains(searchText.lowercased())
        }
    }

    var body: some View {
        NavigationStack {
            NocturneScreen {
                List {
                    if let noneLabel, searchText.isEmpty {
                        Button {
                            onPick(nil)
                            dismiss()
                        } label: {
                            Text(noneLabel).foregroundStyle(TJ.text3)
                        }
                        .listRowBackground(TJ.panel)
                    }
                    ForEach(filtered, id: \.id) { option in
                        Button {
                            onPick(option.id)
                            dismiss()
                        } label: {
                            Text(option.label).foregroundStyle(TJ.text)
                        }
                        .listRowBackground(TJ.panel)
                    }
                }
                .searchable(text: $searchText)
            }
            .navigationTitle(title)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
            }
        }
        .preferredColorScheme(.dark)
    }
}

// MARK: - Card picker

struct CardPickerView: View {
    let deckId: Int64
    let onPick: (NewEntryView.PickedCard) -> Void

    @EnvironmentObject private var appModel: AppModel
    @Environment(\.dismiss) private var dismiss
    @State private var searchText = ""
    @State private var cards: [(id: Int64, name: String)] = []

    var filtered: [(id: Int64, name: String)] {
        guard !searchText.isEmpty else { return cards }
        return cards.filter { $0.name.lowercased().contains(searchText.lowercased()) }
    }

    var body: some View {
        NavigationStack {
            NocturneScreen {
                List(filtered, id: \.id) { card in
                    Button {
                        onPick(.init(cardId: card.id, name: card.name))
                        dismiss()
                    } label: {
                        HStack(spacing: 10) {
                            CardImageView(cardId: card.id)
                                .frame(width: 30, height: 46)
                                .clipShape(RoundedRectangle(cornerRadius: 3))
                            Text(card.name).foregroundStyle(TJ.text)
                        }
                    }
                    .listRowBackground(TJ.panel)
                }
                .searchable(text: $searchText, prompt: "Card name…")
            }
            .navigationTitle("Choose a card")
            .navigationBarTitleDisplayMode(.inline)
        }
        .task {
            cards = (try? appModel.database.writer.read { db in
                try Row.fetchAll(
                    db, sql: "SELECT id, name FROM cards WHERE deck_id = ? ORDER BY card_order, id",
                    arguments: [deckId]).map { ($0["id"], $0["name"]) }
            }) ?? []
        }
    }
}
