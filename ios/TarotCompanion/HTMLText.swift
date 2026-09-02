import SwiftUI

/// Renders the desktop app's rich-text HTML (notes, reference
/// entries) as native attributed text, restyled to the Nocturne
/// palette. Conversion runs off the first render to keep scrolling
/// smooth on long texts.
struct HTMLText: View {
    let html: String
    @State private var attributed: AttributedString?

    var body: some View {
        Group {
            if let attributed {
                Text(attributed)
            } else {
                // Plain-text fallback while (or if) conversion runs.
                Text(Self.strippedPlainText(html))
            }
        }
        .font(.callout)
        .foregroundStyle(TJ.text3)
        .frame(maxWidth: .infinity, alignment: .leading)
        .task(id: html) {
            attributed = await Self.convert(html)
        }
    }

    static func strippedPlainText(_ html: String) -> String {
        html.replacingOccurrences(of: "<[^>]+>", with: " ",
                                  options: .regularExpression)
            .replacingOccurrences(of: "&amp;", with: "&")
            .replacingOccurrences(of: "&nbsp;", with: " ")
            .trimmingCharacters(in: .whitespacesAndNewlines)
    }

    @MainActor
    static func convert(_ html: String) async -> AttributedString? {
        // NSAttributedString's HTML importer is main-actor-bound.
        let styled = """
            <style>
              body { font-family: -apple-system; font-size: 15px; }
            </style>
            \(html)
            """
        guard let data = styled.data(using: .utf8),
              let ns = try? NSMutableAttributedString(
                data: data,
                options: [.documentType: NSAttributedString.DocumentType.html,
                          .characterEncoding: String.Encoding.utf8.rawValue],
                documentAttributes: nil) else { return nil }
        // The importer bakes in black text; recolor for the dark ground.
        ns.removeAttribute(.foregroundColor, range: NSRange(location: 0, length: ns.length))
        return try? AttributedString(ns, including: \.uiKit)
    }
}
