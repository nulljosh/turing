// Reads the text in an image with macOS Vision, one line per recognized line, top to bottom.
// Usage: swift ocr.swift image.png     (tools_util.read_screen calls it on a fresh screenshot)
//        swift ocr.swift --boxes image.png   first line "SCREEN<TAB>width<TAB>height" in points (main display),
//        then "x<TAB>y<TAB>w<TAB>h<TAB>text" per line, as fractions of the image with the origin top-left (tools_gui)
import Foundation
import Vision
import AppKit

let boxes = CommandLine.arguments.contains("--boxes")
let paths = CommandLine.arguments.dropFirst().filter { $0 != "--boxes" }
guard let path = paths.first,
      let image = NSImage(contentsOfFile: path),
      let cg = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    FileHandle.standardError.write("no image\n".data(using: .utf8)!)
    exit(1)
}
let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.usesLanguageCorrection = true
try VNImageRequestHandler(cgImage: cg, options: [:]).perform([request])
let lines = (request.results ?? []).sorted { $0.boundingBox.midY > $1.boundingBox.midY }
if boxes {
    let size = NSScreen.main?.frame.size ?? .zero
    print("SCREEN\t\(size.width)\t\(size.height)")
}
for o in lines {
    guard let t = o.topCandidates(1).first else { continue }
    if boxes {
        let b = o.boundingBox  // Vision: fractions, origin bottom-left
        print("\(b.minX)\t\(1 - b.maxY)\t\(b.width)\t\(b.height)\t\(t.string)")
    } else {
        print(t.string)
    }
}
