import SwiftUI
import UIKit

/// The desktop app's Nocturne palette, mirrored from
/// frontend/src/styles/tokens.css so the phone reads as the same
/// product. Values are the resolved hexes of the --tj-* tokens.
enum TJ {
    // Grounds
    static let canvas = Color(hex: 0x161826)
    static let canvasLift = Color(hex: 0x232544)
    static let panel = Color(red: 29 / 255, green: 31 / 255, blue: 46 / 255).opacity(0.66)
    static let panelSolid = Color(hex: 0x1d1f2e)
    static let well = Color(hex: 0x161826).opacity(0.7)
    static let card = Color(hex: 0x242737)

    // Accent (#9184d9) and tints
    static let accent = Color(hex: 0x9184d9)
    static let tint = accent.opacity(0.14)
    static let tintStrong = accent.opacity(0.20)
    static let textOnTint = Color(hex: 0xe7e5fe)
    static let textAccent = Color(hex: 0xd2cefd)

    // Text roles
    static let text = Color(hex: 0xe9e9ed)
    static let text2 = Color(hex: 0xcfd3e5)   // headings on panels
    static let text3 = Color(hex: 0xb2b6ca)   // secondary prose
    static let textMuted = Color(hex: 0x9397ab)
    static let textFaint = Color(hex: 0x75798c)

    // Line
    static let hairline = Color(hex: 0xe9e9ed).opacity(0.10)

    /// The window-top radial wash every desktop screen sits on.
    static var canvasGradient: some View {
        RadialGradient(
            colors: [canvasLift, canvas],
            center: .init(x: 0.5, y: -0.1),
            startRadius: 0, endRadius: 700)
            .ignoresSafeArea()
            .background(canvas.ignoresSafeArea())
    }

    /// Configure UIKit chrome (nav bars, tab bar) once at launch —
    /// SwiftUI still routes these through UIKit appearance proxies.
    /// Titles get a serif face, echoing the desktop's Newsreader.
    static func applyAppearance() {
        let canvasUI = UIColor(red: 22 / 255, green: 24 / 255, blue: 38 / 255, alpha: 1)
        let textUI = UIColor(red: 233 / 255, green: 233 / 255, blue: 237 / 255, alpha: 1)
        let text2UI = UIColor(red: 207 / 255, green: 211 / 255, blue: 229 / 255, alpha: 1)

        func serif(size: CGFloat, weight: UIFont.Weight) -> UIFont {
            let base = UIFont.systemFont(ofSize: size, weight: weight)
            guard let descriptor = base.fontDescriptor.withDesign(.serif) else { return base }
            return UIFont(descriptor: descriptor, size: size)
        }

        let nav = UINavigationBarAppearance()
        nav.configureWithTransparentBackground()
        nav.largeTitleTextAttributes = [
            .foregroundColor: text2UI,
            .font: serif(size: 34, weight: .light),
        ]
        nav.titleTextAttributes = [
            .foregroundColor: textUI,
            .font: serif(size: 17, weight: .regular),
        ]
        UINavigationBar.appearance().standardAppearance = nav
        UINavigationBar.appearance().scrollEdgeAppearance = nav

        let tab = UITabBarAppearance()
        tab.configureWithDefaultBackground()
        tab.backgroundColor = canvasUI.withAlphaComponent(0.9)
        UITabBar.appearance().standardAppearance = tab
        UITabBar.appearance().scrollEdgeAppearance = tab
    }
}

extension Color {
    init(hex: UInt32) {
        self.init(
            red: Double((hex >> 16) & 0xFF) / 255,
            green: Double((hex >> 8) & 0xFF) / 255,
            blue: Double(hex & 0xFF) / 255)
    }
}

// MARK: - Shared screen scaffolding

/// Wraps a screen in the Nocturne ground so every tab shares the
/// desktop's canvas + top glow.
struct NocturneScreen<Content: View>: View {
    @ViewBuilder var content: Content

    var body: some View {
        ZStack {
            TJ.canvasGradient
            content
        }
        .scrollContentBackground(.hidden)
    }
}
