// Prints the text of a PDF with macOS PDFKit, page by page.
// Usage: swift pdf.swift file.pdf     (tools_util.read_document calls it for .pdf files)
import Foundation
import PDFKit

guard CommandLine.arguments.count > 1, let doc = PDFDocument(url: URL(fileURLWithPath: CommandLine.arguments[1])) else {
    FileHandle.standardError.write("no pdf\n".data(using: .utf8)!)
    exit(1)
}
for i in 0..<doc.pageCount { if let text = doc.page(at: i)?.string { print(text) } }
