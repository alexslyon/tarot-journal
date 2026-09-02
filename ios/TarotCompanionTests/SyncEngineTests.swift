import XCTest
@testable import TarotCompanion
import GRDB

/// End-to-end test of the sync engine against the desktop app running
/// on this Mac (the simulator shares the host's loopback, which the
/// desktop trusts without pairing). Read-only: it only GETs data into
/// an in-memory database. Skips cleanly when the desktop app is not
/// running.
final class SyncEngineTests: XCTestCase {

    private let localServer = URL(string: "http://127.0.0.1:5678")!

    private func desktopIsRunning() async -> Bool {
        var req = URLRequest(url: localServer.appendingPathComponent("api/sync/manifest"))
        req.timeoutInterval = 3
        guard let (_, response) = try? await URLSession.shared.data(for: req),
              let http = response as? HTTPURLResponse else { return false }
        return http.statusCode == 200
    }

    func testLiveSyncPullsData() async throws {
        guard await desktopIsRunning() else {
            throw XCTSkip("Desktop app not running on 127.0.0.1:5678")
        }
        let db = try AppDatabase.empty()
        try db.setSyncState("server_url", localServer.absoluteString)
        let engine = SyncEngine(database: db)

        await engine.syncNow()

        let status = await MainActor.run { engine.statusMessage }
        XCTAssertNil(status, "Sync reported an error: \(status ?? "")")

        let counts = try await db.writer.read { dbc -> [String: Int] in
            var result: [String: Int] = [:]
            for table in SyncEngine.snapshotTables + ["entries", "source_entries"] {
                result[table] = try Int.fetchOne(
                    dbc, sql: "SELECT COUNT(*) FROM \(table)") ?? 0
            }
            return result
        }
        // The live library always has these; a zero means the pull broke.
        XCTAssertGreaterThan(counts["decks"] ?? 0, 0, "no favorite decks pulled")
        XCTAssertGreaterThan(counts["cards"] ?? 0, 0, "no cards pulled")
        XCTAssertGreaterThan(counts["entries"] ?? 0, 0, "no journal entries pulled")
        XCTAssertGreaterThan(counts["source_entries"] ?? 0, 0, "no reference text pulled")
        XCTAssertGreaterThan(counts["spreads"] ?? 0, 0, "no spreads pulled")

        // Entry aggregates must carry their children.
        let withReadings = try await db.writer.read { dbc in
            try Int.fetchOne(dbc, sql: """
                SELECT COUNT(*) FROM entries
                WHERE readings_json IS NOT NULL AND readings_json != '[]'
                """) ?? 0
        }
        XCTAssertGreaterThan(withReadings, 0, "entries synced without their readings")

        // A second sync with the stored cursor should be a no-op delta
        // (nothing changed in the last second) and must not error.
        await engine.syncNow()
        let status2 = await MainActor.run { engine.statusMessage }
        XCTAssertNil(status2)
    }

    func testLocalDatabaseSchema() throws {
        let db = try AppDatabase.empty()
        try db.setSyncState("hello", "world")
        XCTAssertEqual(try db.syncState("hello"), "world")
        try db.setSyncState("hello", nil)
        XCTAssertNil(try db.syncState("hello"))
    }
}
