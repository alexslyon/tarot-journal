import SwiftUI
import GRDB

struct EntryRow: Identifiable, Hashable {
    let id: Int64
    let title: String?
    let readingDatetime: String?
    let content: String?
}

struct JournalListView: View {
    @EnvironmentObject private var appModel: AppModel
    @State private var entries: [EntryRow] = []
    @State private var searchText = ""

    var filtered: [EntryRow] {
        guard !searchText.isEmpty else { return entries }
        let q = searchText.lowercased()
        return entries.filter {
            ($0.title ?? "").lowercased().contains(q)
                || ($0.content ?? "").lowercased().contains(q)
        }
    }

    var body: some View {
        NavigationStack {
            NocturneScreen {
                if entries.isEmpty {
                    ContentUnavailableView(
                        "No entries yet",
                        systemImage: "book.closed",
                        description: Text("Pair with your Mac in Settings, then sync."))
                } else {
                    List(filtered) { entry in
                        NavigationLink(value: entry.id) {
                            VStack(alignment: .leading, spacing: 3) {
                                Text(entry.title ?? "Untitled reading")
                                    .font(.headline)
                                    .fontDesign(.serif)
                                    .fontWeight(.regular)
                                    .foregroundStyle(TJ.text)
                                if let date = entry.readingDatetime {
                                    Text(Self.displayDate(date))
                                        .font(.caption)
                                        .foregroundStyle(TJ.textFaint)
                                }
                            }
                        }
                        .listRowBackground(TJ.panel)
                    }
                    .searchable(text: $searchText)
                    .navigationDestination(for: Int64.self) { entryId in
                        EntryDetailView(entryId: entryId)
                    }
                }
            }
            .navigationTitle("Journal")
        }
        .task { load() }
        .onReceive(appModel.sync.$lastSyncDate) { _ in load() }
    }

    private func load() {
        entries = (try? appModel.database.writer.read { db in
            try Row.fetchAll(db, sql: """
                SELECT id, title, reading_datetime, content
                FROM entries ORDER BY reading_datetime DESC
                """).map {
                EntryRow(id: $0["id"], title: $0["title"],
                         readingDatetime: $0["reading_datetime"],
                         content: $0["content"])
            }
        }) ?? []
    }

    /// The desktop stores naive local timestamps (no timezone), e.g.
    /// "2026-09-01T00:45:12.345" — try its variants oldest-first.
    static func displayDate(_ iso: String) -> String {
        let patterns = [
            "yyyy-MM-dd'T'HH:mm:ss.SSSSSS",
            "yyyy-MM-dd'T'HH:mm:ss",
            "yyyy-MM-dd'T'HH:mm",
            "yyyy-MM-dd",
        ]
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        for pattern in patterns {
            formatter.dateFormat = pattern
            if let date = formatter.date(from: iso) {
                return date.formatted(date: .abbreviated, time: .shortened)
            }
        }
        return iso
    }
}
