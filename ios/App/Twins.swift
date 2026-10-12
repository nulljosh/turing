// Her exact router and 49 exact tools, straight from web/samantha.js in JavaScriptCore: the same file the landing page
// runs and the Mac's parity check diffs word for word against tools.py. Instant, offline, no model. Tools that read a
// real Mac (disk, Wi-Fi, Finder, Shortcuts) are marked NEEDS_MAC in that file and go to the paired Mac instead.
import Foundation
import JavaScriptCore

final class Twins {
    static let shared = Twins()
    private let ctx = JSContext()!
    private let samantha: JSValue?
    private(set) var needsMac: Set<String> = []

    private init() {
        ctx.exceptionHandler = { _, e in NSLog("samantha.js: \(e?.toString() ?? "?")") }
        // JavaScriptCore has no localStorage, so "remember that my dog is Biscuit" would say Remembered and keep nothing.
        // Her memory file on the phone is this one key, in the phone's own storage and nowhere else.
        let store: @convention(block) (String) -> Any = { UserDefaults.standard.string(forKey: "memory." + $0) ?? NSNull() }
        let put: @convention(block) (String, String) -> Void = { UserDefaults.standard.set($1, forKey: "memory." + $0) }
        ctx.setObject(["getItem": store, "setItem": put], forKeyedSubscript: "localStorage" as NSString)
        if let url = Bundle.main.url(forResource: "samantha", withExtension: "js"), let src = try? String(contentsOf: url, encoding: .utf8) {
            ctx.evaluateScript(src)
        }
        samantha = ctx.objectForKeyedSubscript("Samantha")
        if let list = samantha?.forProperty("util")?.forProperty("NEEDS_MAC")?.toArray() as? [String] { needsMac = Set(list) }
    }

    enum Route: Equatable {
        case tool(String, String)   // an exact command: tool name and its argument
        case agent                  // multi-step work the Mac's agent would plan
        case none                   // not a command
    }

    /// What the exact router makes of one line, the same answer the Mac's regex table gives.
    func route(_ text: String) -> Route {
        guard let r = samantha?.invokeMethod("route", withArguments: [text]), !r.isNull, !r.isUndefined else { return .none }
        if r.forProperty("agent")?.toBool() == true { return .agent }
        guard let tool = r.forProperty("tool")?.toString(), !tool.isEmpty, tool != "undefined" else { return .none }
        return .tool(tool, r.forProperty("arg")?.toString() ?? "")
    }

    /// The quick exact answers that need no tool call (arithmetic, "15% of 240", unit sums, the local time), or nil.
    func exact(_ text: String) -> String? {
        guard let a = samantha?.invokeMethod("exact", withArguments: [text]), !a.isNull, !a.isUndefined else { return nil }
        let s = a.toString() ?? ""
        return s.isEmpty || s == "undefined" ? nil : s
    }

    /// The remembered facts that bear on a question, up to three, to hand the on-phone model (the Mac does the same in chat.py).
    func memoryContext(_ question: String) -> [String] {
        (samantha?.invokeMethod("memoryContext", withArguments: [question])?.toArray() as? [String]) ?? []
    }

    /// True when the JavaScript twin of this tool exists and runs without a Mac.
    func runsHere(_ tool: String) -> Bool {
        guard !needsMac.contains(tool), let fn = samantha?.forProperty("util")?.forProperty(tool) else { return false }
        return !fn.isUndefined && !fn.isNull
    }

    /// Runs one exact tool's twin: the same words the Mac's Python version says.
    func run(_ tool: String, _ arg: String) -> String? {
        guard runsHere(tool), let out = samantha?.forProperty("util")?.invokeMethod(tool, withArguments: [arg]) else { return nil }
        return out.isUndefined || out.isNull ? nil : out.toString()
    }
}
