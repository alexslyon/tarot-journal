import Foundation
import Network

/// Browses Bonjour for the desktop app's `_tarotjournal._tcp` service
/// so pairing doesn't require typing an IP address.
///
/// Browsing uses the modern NWBrowser; resolving a service to a
/// concrete IP uses Foundation's NetService, which (though marked
/// deprecated) reliably surfaces the address records, where
/// NWConnection's currentPath does not always.
@MainActor
final class ServerDiscovery: NSObject, ObservableObject {
    struct FoundServer: Identifiable, Hashable {
        let id = UUID()
        let name: String
    }

    @Published var servers: [FoundServer] = []
    private var browser: NWBrowser?
    private var resolvingService: NetService?
    private var resolveCompletion: ((URL?) -> Void)?
    private var resolveTimeout: Task<Void, Never>?

    func start() {
        stop()
        let browser = NWBrowser(
            for: .bonjour(type: "_tarotjournal._tcp", domain: nil),
            using: .tcp)
        browser.browseResultsChangedHandler = { [weak self] results, _ in
            let found = results.compactMap { result -> FoundServer? in
                if case let .service(name, _, _, _) = result.endpoint {
                    return FoundServer(name: name)
                }
                return nil
            }
            Task { @MainActor in self?.servers = found }
        }
        browser.start(queue: .main)
        self.browser = browser
    }

    func stop() {
        browser?.cancel()
        browser = nil
        cancelResolve()
    }

    private func cancelResolve() {
        resolvingService?.stop()
        resolvingService = nil
        resolveTimeout?.cancel()
        resolveTimeout = nil
        resolveCompletion = nil
    }

    /// Resolve a discovered service to a plain http URL the sync
    /// engine can use. Completion fires once, on the main actor.
    func resolve(_ server: FoundServer, completion: @escaping (URL?) -> Void) {
        cancelResolve()
        let service = NetService(domain: "local.",
                                 type: "_tarotjournal._tcp.",
                                 name: server.name)
        service.delegate = self
        resolvingService = service
        resolveCompletion = completion
        service.resolve(withTimeout: 8)
        resolveTimeout = Task { @MainActor [weak self] in
            try? await Task.sleep(for: .seconds(9))
            guard let self, self.resolveCompletion != nil else { return }
            self.finishResolve(url: nil)
        }
    }

    private func finishResolve(url: URL?) {
        let completion = resolveCompletion
        cancelResolve()
        completion?(url)
    }

    /// Pick a usable address from the resolved records, IPv4 first.
    nonisolated private static func url(from service: NetService) -> URL? {
        var v4: String?
        var v6: String?
        for data in service.addresses ?? [] {
            data.withUnsafeBytes { (raw: UnsafeRawBufferPointer) in
                guard let base = raw.baseAddress else { return }
                let family = base.assumingMemoryBound(to: sockaddr.self).pointee.sa_family
                var host = [CChar](repeating: 0, count: Int(NI_MAXHOST))
                let ok = getnameinfo(
                    base.assumingMemoryBound(to: sockaddr.self),
                    socklen_t(data.count),
                    &host, socklen_t(host.count),
                    nil, 0, NI_NUMERICHOST) == 0
                guard ok else { return }
                let ip = String(cString: host)
                if family == sa_family_t(AF_INET), v4 == nil {
                    v4 = ip
                } else if family == sa_family_t(AF_INET6), v6 == nil {
                    v6 = ip
                }
            }
        }
        if let v4 { return URL(string: "http://\(v4):\(service.port)") }
        if let v6 {
            // Scoped link-local addresses need the zone percent-encoded.
            let escaped = v6.replacingOccurrences(of: "%", with: "%25")
            return URL(string: "http://[\(escaped)]:\(service.port)")
        }
        return nil
    }
}

extension ServerDiscovery: NetServiceDelegate {
    nonisolated func netServiceDidResolveAddress(_ sender: NetService) {
        let url = Self.url(from: sender)
        Task { @MainActor in self.finishResolve(url: url) }
    }

    nonisolated func netService(_ sender: NetService,
                                didNotResolve errorDict: [String: NSNumber]) {
        Task { @MainActor in self.finishResolve(url: nil) }
    }
}
