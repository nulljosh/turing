// The conversation: her text plain on the paper, yours in a soft bubble on the right, a quiet row while she works.
import SwiftUI

struct ChatView: View {
    @Environment(Store.self) private var store

    var body: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 18) {
                    ForEach(store.current.messages) { m in
                        MessageRow(message: m, isLast: m.id == store.current.messages.last?.id)
                    }
                    if let w = store.working { WorkingRow(text: w) }
                    Color.clear.frame(height: 1).id("end")
                }
                .padding(.horizontal, 16).padding(.top, 8)
            }
            .scrollDismissesKeyboard(.interactively)
            .onChange(of: store.current.messages.count) { _, _ in withAnimation { proxy.scrollTo("end") } }
            .onChange(of: store.working) { _, _ in withAnimation { proxy.scrollTo("end") } }
        }
    }
}

struct MessageRow: View {
    @Environment(Store.self) private var store
    let message: Message
    let isLast: Bool

    var body: some View {
        if message.role == .user {
            HStack {
                Spacer(minLength: 48)
                Text(message.text)
                    .font(Theme.body).foregroundStyle(Theme.ink)
                    .padding(.horizontal, 14).padding(.vertical, 10)
                    .background(Theme.bubble)
                    .clipShape(RoundedRectangle(cornerRadius: 18, style: .continuous))
            }
        } else {
            VStack(alignment: .leading, spacing: 8) {
                // Prose with inline Markdown; every ``` fence becomes a code block with its own Copy button.
                ForEach(Array(replySegments(message.text).enumerated()), id: \.offset) { _, seg in
                    if let lang = seg.lang {
                        CodeBlock(code: seg.text, lang: lang)
                    } else {
                        Text(inlineMarkdown(seg.text))
                            .font(Theme.body).lineSpacing(Theme.bodyLine).foregroundStyle(Theme.ink)
                            .textSelection(.enabled)
                    }
                }
                if let model = message.model {
                    Text("Answered by \(model)").font(Theme.small).foregroundStyle(Theme.muted)
                }
                if isLast {
                    HStack(spacing: 18) {
                        Button { copyToClipboard(message.text) } label: { Image(systemName: "doc.on.doc") }
                            .accessibilityLabel("Copy")
                        Button { store.retry() } label: { Image(systemName: "arrow.clockwise") }
                            .accessibilityLabel("Retry")
                    }
                    .font(.system(size: 15)).foregroundStyle(Theme.muted)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }
}

/// One code block: monospaced, scrolls sideways instead of wrapping, with a Copy button that says Copied.
struct CodeBlock: View {
    let code: String
    let lang: String
    @State private var copied = false

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                Text(lang.isEmpty ? "code" : lang).font(Theme.small).foregroundStyle(Theme.muted)
                Spacer()
                Button {
                    copyToClipboard(code)
                    copied = true
                    Task { try? await Task.sleep(for: .seconds(1.5)); copied = false }
                } label: {
                    Label(copied ? "Copied" : "Copy", systemImage: copied ? "checkmark" : "doc.on.doc").font(Theme.small)
                }
                .buttonStyle(.plain).foregroundStyle(Theme.muted).accessibilityLabel("Copy code")
            }
            .padding(.horizontal, 12).padding(.vertical, 8)
            Divider().overlay(Theme.line)
            ScrollView(.horizontal, showsIndicators: false) {
                Text(highlight(code, lang: lang)).font(.system(size: 14, design: .monospaced)).foregroundStyle(Theme.ink)
                    .textSelection(.enabled).fixedSize(horizontal: true, vertical: false).padding(12)
            }
        }
        .background(Theme.field)
        .overlay(RoundedRectangle(cornerRadius: 12, style: .continuous).stroke(Theme.line))
        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
    }
}

struct WorkingRow: View {
    let text: String

    var body: some View {
        HStack(spacing: 8) {
            ProgressView().controlSize(.small)
            Text("Working: \(text)").font(Theme.small).foregroundStyle(Theme.muted).lineLimit(1)
        }
        .padding(.horizontal, 12).padding(.vertical, 7)
        .background(Theme.bubble)
        .clipShape(Capsule())
    }
}

/// Before anything changes on the Mac: what she is about to do, and your yes or no.
struct ConfirmSheet: View {
    @Environment(Store.self) private var store

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("She wants to run").font(Theme.small).foregroundStyle(Theme.muted)
            Text(store.pendingConfirm.map { "\($0.name)(\($0.args.joined(separator: ", ")))" } ?? "")
                .font(.system(size: 17, weight: .medium, design: .monospaced)).foregroundStyle(Theme.ink)
            if let note = store.pendingConfirm?.note { Text(note).font(Theme.body).foregroundStyle(Theme.muted) }
            HStack(spacing: 12) {
                Button("No") { store.answerConfirm(false) }
                    .frame(maxWidth: .infinity).padding(.vertical, 12).background(Theme.bubble).foregroundStyle(Theme.ink)
                    .clipShape(Capsule())
                Button("Yes, do it") { store.answerConfirm(true) }
                    .frame(maxWidth: .infinity).padding(.vertical, 12).background(Theme.accent).foregroundStyle(.white)
                    .clipShape(Capsule())
            }
            .font(Theme.title)
        }
        .padding(24)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Theme.paper)
        .presentationDetents([.height(220)])
        .presentationDragIndicator(.visible)
    }
}
