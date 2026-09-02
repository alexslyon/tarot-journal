import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var appModel: AppModel
    @StateObject private var discovery = ServerDiscovery()

    @State private var pairingCode = ""
    @State private var manualAddress = ""
    @State private var selectedURL: URL?
    @State private var selectedName: String?
    @State private var isPairing = false
    @State private var errorMessage: String?
    @State private var paired = false

    var body: some View {
        NavigationStack {
            NocturneScreen {
                Form {
                    Group {
                        if paired {
                            pairedSection
                        } else {
                            pairingSection
                        }
                    }
                    .listRowBackground(TJ.panel)
                }
            }
            .navigationTitle("Settings")
        }
        .onAppear {
            paired = appModel.sync.isPaired
            if !paired { discovery.start() }
        }
        .onDisappear { discovery.stop() }
    }

    // MARK: - Paired state

    private var pairedSection: some View {
        Section("Sync") {
            LabeledContent("Mac", value: appModel.sync.serverURL?.host() ?? "—")
            if let last = appModel.sync.lastSyncDate {
                LabeledContent("Last sync",
                               value: last.formatted(date: .omitted, time: .shortened))
            }
            if let status = appModel.sync.statusMessage {
                Text(status).font(.caption).foregroundStyle(.secondary)
            }
            if let progress = appModel.sync.imageProgress {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Downloading card images — \(progress.done) of \(progress.total)")
                        .font(.caption)
                        .foregroundStyle(TJ.text3)
                    ProgressView(value: Double(progress.done),
                                 total: Double(max(progress.total, 1)))
                        .tint(TJ.accent)
                    Text("Keep the Mac awake with the desktop app open. If this is interrupted, the next sync picks up where it left off.")
                        .font(.caption2)
                        .foregroundStyle(TJ.textFaint)
                }
            }
            Button {
                Task { await appModel.sync.syncNow() }
            } label: {
                if appModel.sync.isSyncing {
                    HStack { ProgressView(); Text("Syncing…") }
                } else {
                    Text("Sync now")
                }
            }
            .disabled(appModel.sync.isSyncing)

            Button("Unpair from this Mac", role: .destructive) {
                appModel.sync.unpair()
                paired = false
                discovery.start()
            }
        }
    }

    // MARK: - Pairing flow

    @ViewBuilder
    private var pairingSection: some View {
        Section("Find your Mac") {
            if discovery.servers.isEmpty {
                HStack {
                    ProgressView()
                    Text("Looking for the Tarot Journal app on your Wi-Fi…")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            ForEach(discovery.servers) { server in
                Button {
                    discovery.resolve(server) { url in
                        selectedURL = url
                        selectedName = server.name
                        if url == nil {
                            errorMessage = "Couldn't resolve \(server.name)'s address. "
                                + "Check that Local Network access is allowed "
                                + "(Settings → Apps → Tarot Companion), or enter "
                                + "the Mac's address below."
                        }
                    }
                } label: {
                    HStack {
                        Text(server.name)
                        Spacer()
                        if selectedName == server.name && selectedURL != nil {
                            Image(systemName: "checkmark")
                        }
                    }
                }
            }
        }

        Section("Or enter the address manually") {
            TextField("192.168.x.x", text: $manualAddress)
                .keyboardType(.numbersAndPunctuation)
                .autocorrectionDisabled()
                .textInputAutocapitalization(.never)
        }

        Section("Pairing code") {
            TextField("6-digit code from the Mac's Settings", text: $pairingCode)
                .keyboardType(.numberPad)
            Button {
                Task { await doPair() }
            } label: {
                if isPairing {
                    HStack { ProgressView(); Text("Pairing…") }
                } else {
                    Text("Pair")
                }
            }
            .disabled(pairingCode.count != 6 || isPairing
                      || (selectedURL == nil && manualAddress.isEmpty))
            if let errorMessage {
                Text(errorMessage).font(.caption).foregroundStyle(.red)
            }
            Text("On the Mac: Settings → General → Phone Sync → Show pairing code.")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    }

    private func doPair() async {
        errorMessage = nil
        var host = selectedURL
        if host == nil, !manualAddress.isEmpty {
            let raw = manualAddress.contains("://")
                ? manualAddress : "http://\(manualAddress):5678"
            host = URL(string: raw)
        }
        guard let host else {
            errorMessage = "Pick your Mac from the list or enter its address."
            return
        }
        isPairing = true
        defer { isPairing = false }
        do {
            try await appModel.sync.pair(
                host: host, code: pairingCode,
                deviceName: UIDevice.current.name)
            paired = true
            discovery.stop()
            await appModel.sync.syncNow()
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
