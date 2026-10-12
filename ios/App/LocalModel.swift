// Her models, on the phone. The tool picker is the Kaggle-trained Qwen2.5-1.5B (4-bit MLX, the same weights the Mac
// uses) and a small instruct model answers the rest. Both download from Hugging Face on first use and stay in the
// app's own storage; nothing leaves the phone. MLX runs on the GPU of a real iPhone, not the simulator.
import Foundation
import HuggingFace
import MLXHuggingFace
import MLXLLM
import MLXLMCommon
import Tokenizers

@Observable
final class LocalModel {
    enum State: Equatable {
        case idle, downloading(Double), ready, failed(String)
    }

    static let handsID = "trommatic/samantha-hands-1.5b-mlx"
    static let chatID = "mlx-community/Qwen2.5-1.5B-Instruct-4bit"
    /// The exact prompt app/tools_agent.py sends the picker.
    static let handsSystem = "You are Samantha's hands. Reply with one JSON tool call. If this is not a command, reply {\"tool\": null, \"arg\": \"\"}."
    static let chatSystem = "You are Samantha, a small assistant that runs on this phone. Answer in plain language and briefly: a few sentences unless the question truly needs more, code when code is asked for, in a ``` fence that names the language. No markdown headers. If you are not sure, say so instead of guessing."

    var state: State = .idle
    private var hands: ModelContainer?
    private var chat: ModelContainer?

    var isReady: Bool { state == .ready }

    /// Downloads (first time) and loads both models. Safe to call again; a loaded pair is kept.
    @MainActor
    func load() async {
        if hands != nil, chat != nil { state = .ready; return }
        state = .downloading(0)
        do {
            hands = try await #huggingFaceLoadModelContainer(configuration: ModelConfiguration(id: Self.handsID)) { [weak self] progress in
                Task { @MainActor in self?.state = .downloading(progress.fractionCompleted / 2) }
            }
            chat = try await #huggingFaceLoadModelContainer(configuration: ModelConfiguration(id: Self.chatID)) { [weak self] progress in
                Task { @MainActor in self?.state = .downloading(0.5 + progress.fractionCompleted / 2) }
            }
            state = .ready
        } catch {
            state = .failed(error.localizedDescription)
        }
    }

    /// The picker's call for one sentence: (tool, arg), or nil when it says this is not a command or answers badly.
    func pick(_ text: String) async throws -> (tool: String, arg: String)? {
        guard let hands else { return nil }
        let session = ChatSession(hands, instructions: Self.handsSystem)
        let raw = try await session.respond(to: text)
        guard let start = raw.firstIndex(of: "{"), let end = raw.lastIndex(of: "}"),
              let json = try? JSONSerialization.jsonObject(with: Data(raw[start...end].utf8)) as? [String: Any],
              let tool = json["tool"] as? String, !tool.isEmpty else { return nil }
        return (tool, (json["arg"] as? String) ?? "")
    }

    /// The instruct model's answer, streamed as it is written.
    func answer(_ text: String) -> AsyncThrowingStream<String, Error> {
        guard let chat else {
            return AsyncThrowingStream { $0.finish(throwing: BridgeError.noModel) }
        }
        return ChatSession(chat, instructions: Self.chatSystem).streamResponse(to: text)
    }
}
