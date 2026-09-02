import SwiftUI
import UIKit

/// Pinch-zoom + pan container (UIScrollView under the hood — SwiftUI
/// has no native equivalent). Content starts fitted and zooms to 5x.
struct ZoomableScrollView<Content: View>: UIViewRepresentable {
    private let content: Content

    init(@ViewBuilder content: () -> Content) {
        self.content = content()
    }

    func makeUIView(context: Context) -> UIScrollView {
        let scrollView = UIScrollView()
        scrollView.delegate = context.coordinator
        scrollView.minimumZoomScale = 1
        scrollView.maximumZoomScale = 5
        scrollView.bouncesZoom = true
        scrollView.showsVerticalScrollIndicator = false
        scrollView.showsHorizontalScrollIndicator = false
        scrollView.backgroundColor = .clear

        let host = context.coordinator.host
        host.rootView = AnyView(content)
        host.view.translatesAutoresizingMaskIntoConstraints = false
        host.view.backgroundColor = .clear
        scrollView.addSubview(host.view)
        NSLayoutConstraint.activate([
            host.view.leadingAnchor.constraint(equalTo: scrollView.contentLayoutGuide.leadingAnchor),
            host.view.trailingAnchor.constraint(equalTo: scrollView.contentLayoutGuide.trailingAnchor),
            host.view.topAnchor.constraint(equalTo: scrollView.contentLayoutGuide.topAnchor),
            host.view.bottomAnchor.constraint(equalTo: scrollView.contentLayoutGuide.bottomAnchor),
            host.view.widthAnchor.constraint(equalTo: scrollView.frameLayoutGuide.widthAnchor),
            host.view.heightAnchor.constraint(equalTo: scrollView.frameLayoutGuide.heightAnchor),
        ])

        // Double-tap toggles between fitted and 2.5x.
        let doubleTap = UITapGestureRecognizer(
            target: context.coordinator,
            action: #selector(Coordinator.handleDoubleTap(_:)))
        doubleTap.numberOfTapsRequired = 2
        scrollView.addGestureRecognizer(doubleTap)
        return scrollView
    }

    func updateUIView(_ uiView: UIScrollView, context: Context) {
        context.coordinator.host.rootView = AnyView(content)
    }

    func makeCoordinator() -> Coordinator { Coordinator() }

    final class Coordinator: NSObject, UIScrollViewDelegate {
        let host = UIHostingController(rootView: AnyView(EmptyView()))

        func viewForZooming(in scrollView: UIScrollView) -> UIView? {
            host.view
        }

        @objc func handleDoubleTap(_ gesture: UITapGestureRecognizer) {
            guard let scrollView = gesture.view as? UIScrollView else { return }
            if scrollView.zoomScale > 1.01 {
                scrollView.setZoomScale(1, animated: true)
            } else {
                let point = gesture.location(in: host.view)
                let size = CGSize(width: scrollView.bounds.width / 2.5,
                                  height: scrollView.bounds.height / 2.5)
                scrollView.zoom(
                    to: CGRect(origin: CGPoint(x: point.x - size.width / 2,
                                               y: point.y - size.height / 2),
                               size: size),
                    animated: true)
            }
        }
    }
}

/// Full-screen single card: pinch to zoom, double-tap to toggle.
struct CardViewerView: View {
    let cardId: Int64?
    let name: String?
    var reversed = false

    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ZStack {
                TJ.canvas.ignoresSafeArea()
                ZoomableScrollView {
                    CardImageView(cardId: cardId, reversed: reversed)
                        .padding(10)
                }
            }
            .navigationTitle(
                (name ?? "Card") + (reversed ? " (reversed)" : ""))
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") { dismiss() }
                }
            }
        }
        .preferredColorScheme(.dark)
    }
}
