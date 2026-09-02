import SwiftUI

@main
struct TarotCompanionApp: App {
    // One shared database and sync engine for the whole app.
    @StateObject private var appModel = AppModel()

    init() {
        TJ.applyAppearance()
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(appModel)
                .preferredColorScheme(.dark)
                .tint(TJ.accent)
        }
    }
}

/// App-wide state: the local database, the sync connection, and
/// whatever the UI needs to observe about them.
@MainActor
final class AppModel: ObservableObject {
    let database: AppDatabase
    let sync: SyncEngine
    let images: ImageStore

    @Published var lastSyncError: String?

    init() {
        do {
            database = try AppDatabase.open()
        } catch {
            // A companion app with no database can't do anything useful;
            // crashing early with a clear message beats limping along.
            fatalError("Could not open the local database: \(error)")
        }
        sync = SyncEngine(database: database)
        let engine = sync
        images = ImageStore(serverURL: { engine.serverURL })

        #if DEBUG && targetEnvironment(simulator)
        // Development convenience: in the simulator, talk to the
        // desktop app on this Mac without pairing (loopback is
        // trusted by the desktop), and pull on every launch so the
        // simulator always shows live data. Never compiled into
        // device builds.
        if engine.serverURL == nil {
            try? database.setSyncState(
                "server_url", "http://127.0.0.1:5678")
        }
        Task { await engine.syncNow() }
        #endif
    }
}
