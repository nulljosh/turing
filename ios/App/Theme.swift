// Samantha for iPhone: the look. Warm paper in light, warm charcoal in dark, one terracotta accent on the send button,
// San Francisco everywhere. No gradients, no shadows, no emojis.
import SwiftUI

enum Theme {
    static let paper = Color(light: 0xFAF9F5, dark: 0x1F1E1D)
    static let ink = Color(light: 0x1F1E1D, dark: 0xF2F0EA)
    static let muted = Color(light: 0x7A7772, dark: 0x9A9791)
    static let line = Color(light: 0xE4E1DA, dark: 0x343230)
    static let bubble = Color(light: 0xEDEAE3, dark: 0x2C2A28)
    static let field = Color(light: 0xFFFFFF, dark: 0x282624)
    static let accent = Color(red: 0xB5 / 255, green: 0x50 / 255, blue: 0x2C / 255)

    static let body = Typeface.sized(17)
    static let bodyLine: CGFloat = 5
    static let title = Typeface.sized(17, weight: .semibold)
    static let greeting = Typeface.sized(28, weight: .semibold, relativeTo: .title)
    static let small = Typeface.sized(13, relativeTo: .footnote)
}

/// Puts text on the clipboard, on either platform.
func copyToClipboard(_ text: String) {
    #if os(iOS)
    UIPasteboard.general.string = text
    #else
    NSPasteboard.general.clearContents(); NSPasteboard.general.setString(text, forType: .string)
    #endif
}

/// Her mark, drawn natively: the same shapes as web/mascot.svg (hair arch, face, round glasses, a smile) in a disc.
struct Mark: View {
    var size: CGFloat = 72

    var body: some View {
        Canvas { ctx, box in
            let s = box.width / 120
            func p(_ x: CGFloat, _ y: CGFloat) -> CGPoint { CGPoint(x: x * s, y: y * s) }
            ctx.fill(Path(ellipseIn: CGRect(origin: .zero, size: box)), with: .color(Color(light: 0xF0EEE8, dark: 0x2A2826)))
            var hair = Path()
            hair.move(to: p(22, 60))
            hair.addArc(center: p(60, 60), radius: 38 * s, startAngle: .degrees(180), endAngle: .degrees(0), clockwise: false)
            hair.addLine(to: p(98, 94)); hair.addQuadCurve(to: p(86, 108), control: p(98, 108))
            hair.addLine(to: p(34, 108)); hair.addQuadCurve(to: p(22, 94), control: p(22, 108)); hair.closeSubpath()
            ctx.fill(hair, with: .color(Color(red: 0xD0 / 255, green: 0x8A / 255, blue: 0x4E / 255)))
            ctx.fill(Path(ellipseIn: CGRect(x: 34 * s, y: 40 * s, width: 52 * s, height: 58 * s)), with: .color(Color(red: 0xF3 / 255, green: 0xDD / 255, blue: 0xC8 / 255)))
            var bangs = Path()
            bangs.move(to: p(34, 64)); bangs.addQuadCurve(to: p(60, 34), control: p(36, 34)); bangs.addQuadCurve(to: p(86, 64), control: p(84, 34))
            bangs.addQuadCurve(to: p(46, 57), control: p(80, 50)); bangs.addQuadCurve(to: p(34, 64), control: p(40, 57)); bangs.closeSubpath()
            ctx.fill(bangs, with: .color(Color(red: 0xD0 / 255, green: 0x8A / 255, blue: 0x4E / 255)))
            let frame = Color(red: 0x4A / 255, green: 0x2C / 255, blue: 0x17 / 255)
            for cx in [48.0, 72.0] {
                ctx.stroke(Path(ellipseIn: CGRect(x: (cx - 11) * s, y: 61 * s, width: 22 * s, height: 22 * s)), with: .color(frame), lineWidth: 3.2 * s)
                ctx.fill(Path(ellipseIn: CGRect(x: (cx - 2.4) * s, y: 70.6 * s, width: 4.8 * s, height: 4.8 * s)), with: .color(Color(red: 0x2A / 255, green: 0x1A / 255, blue: 0x12 / 255)))
            }
            var bridge = Path(); bridge.move(to: p(59, 70.5)); bridge.addLine(to: p(61, 70.5))
            ctx.stroke(bridge, with: .color(frame), style: StrokeStyle(lineWidth: 3.2 * s, lineCap: .round))
            var smile = Path(); smile.move(to: p(53, 90)); smile.addQuadCurve(to: p(67, 90), control: p(60, 95))
            ctx.stroke(smile, with: .color(Theme.accent), style: StrokeStyle(lineWidth: 2.4 * s, lineCap: .round))
        }
        .frame(width: size, height: size)
        .clipShape(Circle())
        .accessibilityLabel("Samantha")
    }
}
