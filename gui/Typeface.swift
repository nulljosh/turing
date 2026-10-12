import SwiftUI
import CoreText
#if os(iOS)
import UIKit
#else
import AppKit
#endif

// Samantha Sans for the Mac app and the iPhone app: one file, the same face the landing page uses (scripts/gen_font.py
// draws it from one stem width and one squircle curve). The three weights ship inside the app as plain TTFs and are
// registered once at launch, no Info.plist keys, so the dev build, the packaged build and the phone all work the same way.
// If the fonts are missing the text falls back to the system font and the self-check says so, instead of looking fine.
enum Typeface {
    static let names = ["Regular", "Medium", "Semibold"].map { "SamanthaSans-\($0)" }

    /// Register the three weights from the app bundle. Safe to call more than once.
    static func register() {
        let urls = names.compactMap { Bundle.main.url(forResource: $0, withExtension: "ttf") ?? Bundle.main.url(forResource: $0, withExtension: "ttf", subdirectory: "Fonts") }
        if !urls.isEmpty { CTFontManagerRegisterFontsForURLs(urls as CFArray, .process, nil) }
    }

    /// True when the regular weight resolves, which is what the self-check asserts.
    static var available: Bool {
        #if os(iOS)
        return UIFont(name: names[0], size: 12) != nil
        #else
        return NSFont(name: names[0], size: 12) != nil
        #endif
    }

    static func name(_ weight: Font.Weight) -> String {
        weight == .semibold || weight == .bold || weight == .heavy || weight == .black ? names[2] : weight == .medium ? names[1] : names[0]
    }

    /// The point size a text style has on this platform, so a style reads the same as the system's did.
    static func size(_ style: Font.TextStyle) -> CGFloat {
        #if os(iOS)
        let sizes: [Font.TextStyle: CGFloat] = [.largeTitle: 34, .title: 28, .title2: 22, .title3: 20, .headline: 17, .body: 17, .callout: 16, .subheadline: 15, .footnote: 13, .caption: 12, .caption2: 11]
        #else
        let sizes: [Font.TextStyle: CGFloat] = [.largeTitle: 26, .title: 22, .title2: 17, .title3: 15, .headline: 13, .body: 13, .callout: 12, .subheadline: 11, .footnote: 10, .caption: 10, .caption2: 10]
        #endif
        return sizes[style] ?? 13
    }

    /// A text style in Samantha Sans, scaling with Dynamic Type; the system face when the fonts did not load.
    static func font(_ style: Font.TextStyle, weight: Font.Weight = .regular) -> Font {
        available ? .custom(name(weight), size: size(style), relativeTo: style) : .system(style).weight(weight)
    }

    /// A fixed point size in Samantha Sans that still scales with Dynamic Type, relative to a style.
    static func sized(_ points: CGFloat, weight: Font.Weight = .regular, relativeTo style: Font.TextStyle = .body) -> Font {
        available ? .custom(name(weight), size: points, relativeTo: style) : .system(size: points, weight: weight)
    }
}
