import SwiftUI

@main
struct TarotCompanionApp: App {
    // One shared database and sync engine for the whole app.
    @StateObject private var appModel = AppModel()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(appModel)
        }
    }
}

/// App-wide state: the local database, the sync connection, and
/// whatever the UI needs to observe about them.
@MainActor
final class AppModel: ObservableObject {
    let database: AppDatabase
    let sync: SyncEngine

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
    }
}
