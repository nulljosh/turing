// Code in her replies, shared by the Mac app (gui/SamanthaGUI.swift) and the phone app (ios/App): the reply splitter
// (prose, code fences, inline Markdown) and the syntax colors. The scanner is the same one as web/highlight.js:
// comments, strings, numbers and keywords, the fence's label only choosing "#" or "//" comments and what 'single quotes'
// mean. It never throws and never stalls on half-written code; an unterminated string or comment runs to the end.
import SwiftUI

/// A reply split on its ``` fences. `lang` is nil for prose, the fence's language ("" when unnamed) for code.
/// A fence left open (a reply cut short) still counts as code. Markdown headers become plain bold lines.
func replySegments(_ text: String) -> [(lang: String?, text: String)] {
    text.components(separatedBy: "```").enumerated().compactMap { i, part in
        if i % 2 == 1 {
            let lines = part.split(separator: "\n", maxSplits: 1, omittingEmptySubsequences: false)
            let first = lines.first.map(String.init) ?? ""
            let isLang = !first.contains(" ") && first.count < 16
            let code = (isLang && lines.count > 1 ? String(lines[1]) : part).trimmingCharacters(in: .newlines)
            return code.isEmpty ? nil : (isLang ? first : "", code)
        }
        let prose = part.replacingOccurrences(of: #"(?m)^#{1,6}\s+(.+)$"#, with: "**$1**", options: .regularExpression)
            .trimmingCharacters(in: .whitespacesAndNewlines)
        return prose.isEmpty ? nil : (nil, prose)
    }
}

/// Bold, italics and `code` inside a sentence, keeping her line breaks.
func inlineMarkdown(_ s: String) -> AttributedString {
    (try? AttributedString(markdown: s, options: .init(interpretedSyntax: .inlineOnlyPreservingWhitespace))) ?? AttributedString(s)
}

enum CodeKind { case plain, comment, string, number, keyword }

private let keywordSet: Set<String> = Set(("if else elif for while do return break continue switch case default goto func fn function def class " +
    "struct enum union trait impl interface protocol extension let var const static mut pub use mod import from as export package type " +
    "typealias in is not and or new delete try catch except finally throw throws raise defer guard where async await yield lambda with " +
    "pass self this super true false nil null None True False void int char long short float double bool boolean string str unsigned " +
    "signed u8 u16 u32 u64 usize i8 i16 i32 i64 isize f32 f64 String Int Bool Double Float Character Self then fi done esac").split(separator: " ").map(String.init))

private let hashLangs: Set<String> = ["python", "py", "bash", "sh", "shell", "zsh", "ruby", "rb", "yaml", "yml", "toml", "r", "perl", "makefile", "dockerfile"]
private let singleQuoteLangs: Set<String> = ["js", "javascript", "jsx", "ts", "tsx", "typescript", "python", "py", "bash", "sh", "shell", "zsh", "ruby", "rb", "php", "json", "sql", "yaml", "yml", "lua", "perl"]

/// The code cut into runs, in order, covering all of it. `lang` is the fence's label ("" when it has none).
func codeTokens(_ code: String, lang: String) -> [(kind: CodeKind, text: String)] {
    let lang = lang.lowercased()
    let hash = hashLangs.contains(lang), sq = singleQuoteLangs.contains(lang)
    let comment = hash ? #"#[^\n]*"# : #"//[^\n]*|/\*[\s\S]*?(?:\*/|\z)"#
    let string = #"""[\s\S]*?(?:"""|\z)|'''[\s\S]*?(?:'''|\z)|"(?:\\.|[^"\\\n])*"?|`(?:\\.|[^`\\])*`?|"# +
        (sq ? #"'(?:\\.|[^'\\\n])*'?"# : #"'(?:\\[^'\n]*|[^'\\\n])'"#)   // Rust's 'a is a lifetime, not a string
    let number = #"0[xX][0-9a-fA-F_]+|\d[\d_]*(?:\.\d+)?(?:[eE][+-]?\d+)?"#
    let word = (hash ? "" : "#?") + #"[A-Za-z_]\w*"#                      // #include, #define in C
    guard let re = try? NSRegularExpression(pattern: "(\(comment))|(\(string))|(\(number))|(\(word))") else { return [(.plain, code)] }
    var out: [(kind: CodeKind, text: String)] = []
    var at = code.startIndex
    for m in re.matches(in: code, range: NSRange(code.startIndex..., in: code)) {
        guard let r = Range(m.range, in: code), !r.isEmpty else { continue }
        let kind: CodeKind = m.range(at: 1).location != NSNotFound ? .comment : m.range(at: 2).location != NSNotFound ? .string
            : m.range(at: 3).location != NSNotFound ? .number : (code[r].hasPrefix("#") || keywordSet.contains(String(code[r]))) ? .keyword : .plain
        if r.lowerBound > at { out.append((.plain, String(code[at..<r.lowerBound]))) }
        out.append((kind, String(code[r]))); at = r.upperBound
    }
    if at < code.endIndex { out.append((.plain, String(code[at...]))) }
    return out
}

extension Color {
    /// One color for each appearance, from two hex values.
    init(light: UInt32, dark: UInt32) {
        func rgb(_ v: UInt32) -> (CGFloat, CGFloat, CGFloat) { (CGFloat((v >> 16) & 0xFF) / 255, CGFloat((v >> 8) & 0xFF) / 255, CGFloat(v & 0xFF) / 255) }
        #if os(iOS)
        self.init(uiColor: UIColor { trait in
            let (r, g, b) = rgb(trait.userInterfaceStyle == .dark ? dark : light)
            return UIColor(red: r, green: g, blue: b, alpha: 1)
        })
        #else
        self.init(nsColor: NSColor(name: nil) { look in
            let (r, g, b) = rgb(look.bestMatch(from: [.aqua, .darkAqua]) == .darkAqua ? dark : light)
            return NSColor(srgbRed: r, green: g, blue: b, alpha: 1)
        })
        #endif
    }
}

/// Her code palette, each pair at least 4.5:1 on white and on the dark code backgrounds (checked when it was chosen):
/// blue keywords, green strings, deep red numbers, gray comments. No yellow, orange, teal or purple anywhere in her look.
private func codeColor(_ kind: CodeKind) -> Color? {
    switch kind {
    case .keyword: return Color(light: 0x0B57D0, dark: 0x7AA7FF)
    case .string: return Color(light: 0x1A7F37, dark: 0x6FCF8E)
    case .number: return Color(light: 0xB3261E, dark: 0xFF8A80)
    case .comment: return Color(light: 0x6B6B6B, dark: 0xA0A0A0)
    case .plain: return nil
    }
}

/// The code as colored text.
func highlight(_ code: String, lang: String) -> AttributedString {
    var out = AttributedString()
    for (kind, text) in codeTokens(code, lang: lang) {
        var piece = AttributedString(text)
        if let c = codeColor(kind) { piece.foregroundColor = c }
        out += piece
    }
    return out
}

/// Asserts for `SamanthaGUI --check` (build.sh runs it): the cases that broke earlier scanners.
func highlightSelfTest() -> Bool {
    func kinds(_ code: String, _ lang: String) -> [String] {
        codeTokens(code, lang: lang).filter { $0.kind != .plain }.map { "\($0.kind):\($0.text)" }
    }
    let samples = ["let a = \"b\\\"c\" // d\n", "echo 'x' `y` #z\n", "if (a) { return \"\n", "😀 \"é\" 0x", "'''", "\"\"\"", "/* open", "", "'a"]
    let covers = samples.allSatisfy { s in ["c", "python", "js", "rust", "bash", ""].allSatisfy { codeTokens(s, lang: $0).map(\.text).joined() == s } }
    return covers
        && kinds("#include <stdio.h>\nint x = 0x1F; // hi", "c") == ["keyword:#include", "keyword:int", "number:0x1F", "comment:// hi"]
        && kinds("# note\nx = 'a'  # tail", "python") == ["comment:# note", "string:'a'", "comment:# tail"]
        && kinds("fn f<'a>(x: &'a str) -> char { 'c' }", "rust") == ["keyword:fn", "keyword:str", "keyword:char", "string:'c'"]
        && kinds("const s = `a${b}`;", "js") == ["keyword:const", "string:`a${b}`"]
        && kinds("def f():\n    \"\"\"if for\n    return\"\"\"\n    return 1.5", "python") == ["keyword:def", "string:\"\"\"if for\n    return\"\"\"", "keyword:return", "number:1.5"]
        && kinds("x1 = 2", "swift") == ["number:2"]
        && kinds("\"abc", "c") == ["string:\"abc"]
        && kinds("/* open", "c") == ["comment:/* open"]
        && replySegments("Here:\n```c\nint x;\n```\nDone").map { $0.lang ?? "-" } == ["-", "c", "-"]
}
