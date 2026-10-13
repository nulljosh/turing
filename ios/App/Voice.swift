// Voice: dictation in (Apple's speech recognizer, on the phone when it can) and her reply read out loud.
// A turn asked by voice is answered by voice; a typed turn stays quiet.
import AVFoundation
import Speech

@Observable
final class Voice {
    static let shared = Voice()
    var listening = false
    var heard = ""                     // the live transcript while the mic is open
    var problem: String? = nil {      // shown above the composer for a few seconds, then gone
        didSet { if let p = problem { DispatchQueue.main.asyncAfter(deadline: .now() + 4) { if self.problem == p { self.problem = nil } } } }
    }

    private let engine = AVAudioEngine()
    private let recognizer = SFSpeechRecognizer()
    private var request: SFSpeechAudioBufferRecognitionRequest?
    private var task: SFSpeechRecognitionTask?
    private let speaker = AVSpeechSynthesizer()

    /// Opens the mic after asking once for speech and microphone access.
    func start() {
        problem = nil
        SFSpeechRecognizer.requestAuthorization { status in
            AVAudioApplication.requestRecordPermission { mic in
                DispatchQueue.main.async {
                    guard status == .authorized, mic else { self.problem = "Turn on Microphone and Speech Recognition for Samantha in Settings."; return }
                    do { try self.open() } catch { self.problem = "The microphone did not start." ; self.stop() }
                }
            }
        }
    }

    private func open() throws {
        guard let recognizer, recognizer.isAvailable else { problem = "Dictation is not available right now."; return }
        speaker.stopSpeaking(at: .immediate)
        #if os(iOS)
        let session = AVAudioSession.sharedInstance()
        try session.setCategory(.playAndRecord, mode: .measurement, options: [.duckOthers, .defaultToSpeaker])
        try session.setActive(true, options: .notifyOthersOnDeactivation)
        #endif
        let req = SFSpeechAudioBufferRecognitionRequest()
        req.shouldReportPartialResults = true
        if recognizer.supportsOnDeviceRecognition { req.requiresOnDeviceRecognition = true }
        request = req
        heard = ""
        let input = engine.inputNode
        let format = input.outputFormat(forBus: 0)
        // No microphone (a Mac mini, a simulator): installing a tap on a zero-channel input crashes, so say so instead.
        guard format.channelCount > 0, format.sampleRate > 0 else { problem = "No microphone found. Plug one in and try again."; return }
        input.removeTap(onBus: 0)
        input.installTap(onBus: 0, bufferSize: 1024, format: format) { buf, _ in req.append(buf) }
        engine.prepare()
        try engine.start()
        listening = true
        task = recognizer.recognitionTask(with: req) { result, error in
            DispatchQueue.main.async {
                if let result { self.heard = result.bestTranscription.formattedString }
                if error != nil || result?.isFinal == true { self.stop() }
            }
        }
    }

    /// Closes the mic and returns what was heard.
    @discardableResult
    func stop() -> String {
        if engine.isRunning { engine.stop(); engine.inputNode.removeTap(onBus: 0) }
        request?.endAudio()
        task?.cancel()
        request = nil; task = nil
        listening = false
        #if os(iOS)
        try? AVAudioSession.sharedInstance().setCategory(.playback, mode: .spokenAudio)
        #endif
        return heard
    }

    /// Reads a reply out loud, without code blocks or Markdown marks.
    func say(_ text: String) {
        let plain = text.replacingOccurrences(of: "```[\\s\\S]*?```", with: " There is code on screen. ", options: .regularExpression)
            .replacingOccurrences(of: "[*_`#>]", with: "", options: .regularExpression)
        guard !plain.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return }
        #if os(iOS)
        try? AVAudioSession.sharedInstance().setCategory(.playback, mode: .spokenAudio)
        try? AVAudioSession.sharedInstance().setActive(true)
        #endif
        let u = AVSpeechUtterance(string: plain)
        u.voice = AVSpeechSynthesisVoice(language: Locale.current.identifier.replacingOccurrences(of: "_", with: "-"))
        speaker.speak(u)
    }
}
