import SwiftUI
import GRDB

/// One reference source's texts for an archetype, grouped by field.
struct SourceSection: Identifiable {
    let id: Int64          // source id
    let sourceName: String
    var fields: [FieldText]

    struct FieldText: Identifiable {
        let id: Int64      // source_entry id
        let fieldName: String
        let content: String
        let sortOrder: Int
    }
}

struct ReferenceDetailView: View {
    let archetypeId: Int64
    let archetypeName: String

    @EnvironmentObject private var appModel: AppModel
    @State private var sections: [SourceSection] = []
    @State private var expandedSources: Set<Int64> = []

    var body: some View {
        NocturneScreen {
            ScrollView {
                VStack(alignment: .leading, spacing: 14) {
                    if sections.isEmpty {
                        ContentUnavailableView(
                            "No reference text",
                            systemImage: "text.book.closed",
                            description: Text("No source has an entry for this card yet."))
                            .padding(.top, 60)
                    }
                    ForEach(sections) { section in
                        sourcePanel(section)
                    }
                }
                .padding()
            }
        }
        .navigationTitle(archetypeName)
        .navigationBarTitleDisplayMode(.inline)
        .task { load() }
    }

    private func sourcePanel(_ section: SourceSection) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Button {
                if expandedSources.contains(section.id) {
                    expandedSources.remove(section.id)
                } else {
                    expandedSources.insert(section.id)
                }
            } label: {
                HStack {
                    Text(section.sourceName)
                        .font(.headline)
                        .fontDesign(.serif)
                        .fontWeight(.regular)
                        .foregroundStyle(TJ.text2)
                    Spacer()
                    Image(systemName: expandedSources.contains(section.id)
                          ? "chevron.down" : "chevron.right")
                        .font(.caption)
                        .foregroundStyle(TJ.textMuted)
                }
            }
            if expandedSources.contains(section.id) {
                ForEach(section.fields) { field in
                    VStack(alignment: .leading, spacing: 4) {
                        Text(field.fieldName)
                            .font(.caption)
                            .textCase(.uppercase)
                            .foregroundStyle(TJ.textMuted)
                        HTMLText(html: field.content)
                    }
                }
            }
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(RoundedRectangle(cornerRadius: 10).fill(TJ.panel))
    }

    private func load() {
        let rows = (try? appModel.database.writer.read { db in
            try Row.fetchAll(db, sql: """
                SELECT se.id, se.content,
                       sf.name AS field_name, sf.sort_order,
                       rs.id AS source_id, rs.name AS source_name
                FROM source_entries se
                JOIN source_fields sf ON sf.id = se.field_id
                JOIN reference_sources rs ON rs.id = sf.source_id
                WHERE se.archetype_id = ?
                ORDER BY rs.name, sf.sort_order
                """, arguments: [archetypeId])
        }) ?? []

        var bySource: [Int64: SourceSection] = [:]
        var order: [Int64] = []
        for row in rows {
            let sourceId: Int64 = row["source_id"]
            let field = SourceSection.FieldText(
                id: row["id"],
                fieldName: row["field_name"] ?? "",
                content: row["content"] ?? "",
                sortOrder: row["sort_order"] ?? 0)
            if bySource[sourceId] == nil {
                bySource[sourceId] = SourceSection(
                    id: sourceId,
                    sourceName: row["source_name"] ?? "Source",
                    fields: [])
                order.append(sourceId)
            }
            bySource[sourceId]?.fields.append(field)
        }
        sections = order.compactMap { bySource[$0] }
        // A single source opens itself; several start collapsed.
        if sections.count == 1, let only = sections.first {
            expandedSources = [only.id]
        }
    }
}
