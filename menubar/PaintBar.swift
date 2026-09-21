// PaintBar: Samantha's painting hands in the menu bar.
// Pick an image, Pixelmator Pro rebuilds it from colored squares. One file, no Xcode project.
// Build: ./build.sh   Self-check: ./build/PaintBar.app/Contents/MacOS/PaintBar --check
import SwiftUI
import AppKit
import UniformTypeIdentifiers

/// The exact command line handed to pxm.py. Pure, so --check can test it without the app.
func paintArguments(pxm: String, image: String, out: String, layers: Int, background: Bool) -> [String] {
    var args = [pxm, "paint", image, "--out", out, "--shapes", String(layers), "--size", "1600"]
    if background { args.append("--headless") }
    return args
}

func outputPath(for image: URL) -> String {
    let name = image.deletingPathExtension().lastPathComponent
    return NSHomeDirectory() + "/Desktop/" + name + "-painting.png"
}

@MainActor
final class Painter: ObservableObject {
    @Published var status = "Ready"
    @Published var busy = false
    @Published var last: String?
    private let pxm = (Bundle.main.object(forInfoDictionaryKey: "PxmPath") as? String) ?? ""

    func pick(layers: Int, background: Bool) {
        let panel = NSOpenPanel()
        panel.allowedContentTypes = [.image]
        panel.allowsMultipleSelection = false
        NSApp.activate(ignoringOtherApps: true)
        guard panel.runModal() == .OK, let url = panel.url else { return }
        paint(url, layers: layers, background: background)
    }

    func paint(_ image: URL, layers: Int, background: Bool) {
        guard !busy else { return }  // Pixelmator can only build one thing at a time
        guard FileManager.default.fileExists(atPath: pxm) else { status = "pxm.py not found. Run build.sh again."; return }
        let out = outputPath(for: image)
        let job = Process()
        job.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
        job.arguments = paintArguments(pxm: pxm, image: image.path, out: out, layers: layers, background: background)
        let pipe = Pipe()
        job.standardError = pipe
        job.standardOutput = Pipe()
        busy = true
        status = "Painting \(image.lastPathComponent), \(layers) layers"
        job.terminationHandler = { done in
            let err = String(data: pipe.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? ""
            Task { @MainActor in
                self.busy = false
                if done.terminationStatus == 0 {
                    self.last = out
                    self.status = "Done: " + (out as NSString).lastPathComponent
                } else {
                    // pxm.py prints "error: ..." then "hint: ...". Show the first line, it is written for people.
                    self.status = err.split(separator: "\n").first.map(String.init) ?? "Pixelmator refused the painting"
                }
            }
        }
        do { try job.run() } catch { busy = false; status = "Could not start python3" }
    }
}

struct PaintMenu: View {
    @ObservedObject var painter: Painter
    @AppStorage("background") private var background = true
    @AppStorage("layers") private var layers = 2000

    var body: some View {
        Text(painter.status)
        Divider()
        Button("Paint an Image…") { painter.pick(layers: layers, background: background) }
            .disabled(painter.busy)
        Button("Show Last Painting") { if let p = painter.last { NSWorkspace.shared.selectFile(p, inFileViewerRootedAtPath: "") } }
            .disabled(painter.last == nil)
        Divider()
        // Settings live in the menu. Two of them do not need a window.
        Toggle("Keep Pixelmator in the Background", isOn: $background)
        Picker("Layers", selection: $layers) {
            Text("800, about half a minute").tag(800)
            Text("2000, a few minutes").tag(2000)
            Text("4000, slow and sharp").tag(4000)
        }
        Divider()
        Button("Quit") { NSApp.terminate(nil) }
    }
}

@main
struct PaintBarApp: App {
    @StateObject private var painter = Painter()

    init() {
        guard CommandLine.arguments.contains("--check") else { return }
        let a = paintArguments(pxm: "/p/pxm.py", image: "/i/a b.jpg", out: "/o.png", layers: 800, background: true)
        precondition(a == ["/p/pxm.py", "paint", "/i/a b.jpg", "--out", "/o.png", "--shapes", "800", "--size", "1600", "--headless"])
        precondition(!paintArguments(pxm: "p", image: "i", out: "o", layers: 2000, background: false).contains("--headless"))
        precondition(outputPath(for: URL(fileURLWithPath: "/x/mona.lisa.jpg")).hasSuffix("/Desktop/mona.lisa-painting.png"))
        print("PaintBar ok")
        exit(0)
    }

    var body: some Scene {
        MenuBarExtra("Samantha Paint", systemImage: painter.busy ? "paintbrush.pointed.fill" : "paintbrush.pointed") {
            PaintMenu(painter: painter)
        }
    }
}
