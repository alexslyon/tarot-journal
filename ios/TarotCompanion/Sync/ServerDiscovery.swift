import Foundation
import Network

/// Browses Bonjour for the desktop app's `_tarotjournal._tcp` service
/// so pairing doesn't require typing an IP address.
@MainActor
final class ServerDiscovery: ObservableObject {
    struct FoundServer: Identifiable, Hashable {
        let id = UUID()
        let name: String
        let endpoint: NWEndpoint
    }

    @Published var servers: [FoundServer] = []
    private var browser: NWBrowser?

    func start() {
        stop()
        let browser = NWBrowser(
            for: .bonjour(type: "_tarotjournal._tcp", domain: nil),
            using: .tcp)
        browser.browseResultsChangedHandler = { [weak self] results, _ in
            let found = results.map { result -> FoundServer in
                if case let .service(name, _, _, _) = result.endpoint {
                    return FoundServer(name: name, endpoint: result.endpoint)
                }
                return FoundServer(name: "Mac", endpoint: result.endpoint)
            }
            Task { @MainActor in self?.servers = found }
        }
        browser.start(queue: .main)
        self.browser = browser
    }

    func stop() {
        browser?.cancel()
        browser = nil
    }

    /// Resolve a discovered service to a plain http URL the sync
    /// engine can use. Completion fires on the main queue.
    func resolve(_ server: FoundServer, completion: @escaping (URL?) -> Void) {
        let connection = NWConnection(to: server.endpoint, using: .tcp)
        connection.stateUpdateHandler = { state in
            if case .ready = state {
                if let inner = connection.currentPath?.remoteEndpoint,
                   case let .hostPort(host, port) = inner {
                    let hostString: String
                    switch host {
                    case .ipv4(let v4): hostString = "\(v4)"
                    case .ipv6(let v6): hostString = "[\(v6)]"
                    case .name(let name, _): hostString = name
                    @unknown default: hostString = "\(host)"
                    }
                    let url = URL(string: "http://\(hostString):\(port.rawValue)")
                    connection.cancel()
                    DispatchQueue.main.async { completion(url) }
                    return
                }
                connection.cancel()
                DispatchQueue.main.async { completion(nil) }
            } else if case .failed = state {
                connection.cancel()
                DispatchQueue.main.async { completion(nil) }
            }
        }
        connection.start(queue: .main)
    }
}
