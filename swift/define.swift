// Prints the macOS dictionary's definition of a word, offline (the same dictionary as the Dictionary app).
// Usage: swift define.swift serendipity    prints nothing when the dictionary has no entry (tools_words.define_word)
import CoreServices
import Foundation

let word = CommandLine.arguments.dropFirst().joined(separator: " ")
guard !word.isEmpty,
      let def = DCSCopyTextDefinition(nil, word as CFString, CFRangeMake(0, (word as NSString).length)) else { exit(0) }
print(def.takeRetainedValue() as String)
