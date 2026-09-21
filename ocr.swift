// Reads the text in an image with macOS Vision, one line per recognized line, top to bottom.
// Usage: swift ocr.swift image.png     (tools_util.read_screen calls it on a fresh screenshot)
import Foundation
import Vision
import AppKit

guard CommandLine.arguments.count > 1,
      let image = NSImage(contentsOfFile: CommandLine.arguments[1]),
      let cg = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    FileHandle.standardError.write("no image\n".data(using: .utf8)!)
    exit(1)
}
let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.usesLanguageCorrection = true
try VNImageRequestHandler(cgImage: cg, options: [:]).perform([request])
let lines = (request.results ?? []).sorted { $0.boundingBox.midY > $1.boundingBox.midY }
for o in lines { if let t = o.topCandidates(1).first { print(t.string) } }
