// Lists what can be clicked in the frontmost app through the macOS accessibility tree, so she can click a button
// that shows an icon and no words. Needs Accessibility allowed for the terminal (same permission cliclick needs).
// Usage: swift ax.swift    prints "AX", then "x<TAB>y<TAB>role<TAB>label" per labeled element, x and y its center
//        in screen points, origin top-left (tools_gui.ax_boxes). Prints only "AX" when nothing can be read.
import AppKit
import ApplicationServices

func attr(_ e: AXUIElement, _ name: String) -> AnyObject? {
    var v: AnyObject?
    return AXUIElementCopyAttributeValue(e, name as CFString, &v) == .success ? v : nil
}

print("AX")
guard AXIsProcessTrusted(), let app = NSWorkspace.shared.frontmostApplication else { exit(0) }
var seen = 0
func walk(_ e: AXUIElement, _ depth: Int) {
    if depth > 30 || seen > 2000 { return }  // a web page can hold thousands; enough to find a button
    seen += 1
    let role = attr(e, kAXRoleAttribute) as? String ?? ""
    let label = [kAXTitleAttribute, kAXDescriptionAttribute, kAXHelpAttribute]
        .compactMap { attr(e, $0) as? String }.first { !$0.isEmpty }
        ?? (role == "AXStaticText" ? attr(e, kAXValueAttribute) as? String : nil)
    var p = CGPoint.zero, s = CGSize.zero
    if let label, let pv = attr(e, kAXPositionAttribute), let sv = attr(e, kAXSizeAttribute),
       AXValueGetValue(pv as! AXValue, .cgPoint, &p), AXValueGetValue(sv as! AXValue, .cgSize, &s), s.width > 0 {
        let flat = label.replacingOccurrences(of: "\n", with: " ").replacingOccurrences(of: "\t", with: " ")
        print("\(Int(p.x + s.width / 2))\t\(Int(p.y + s.height / 2))\t\(role)\t\(flat)")
    }
    for child in (attr(e, kAXChildrenAttribute) as? [AXUIElement]) ?? [] { walk(child, depth + 1) }
}
walk(AXUIElementCreateApplication(app.processIdentifier), 0)
