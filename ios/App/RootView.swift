// The one screen: a top bar, the home greeting or the conversation, the composer, and the history drawer over it.
import SwiftUI

struct RootView: View {
    @Environment(Store.self) private var store
    @State private var drawer = false
    @State private var settings = false
    @State private var splash = true

    var body: some View {
        @Bindable var store = store
        ZStack(alignment: .leading) {
            if splash {
                Splash().zIndex(2).transition(.opacity)
                    .task { try? await Task.sleep(for: .seconds(1.8)); withAnimation(.easeOut(duration: 0.4)) { splash = false } }
            }
            VStack(spacing: 0) {
                TopBar(onMenu: { hideKeyboard(); withAnimation(.easeOut(duration: 0.22)) { drawer = true } }, onNew: { store.newChat() })
                if store.current.messages.isEmpty { HomeView() } else { ChatView() }
                Composer()
            }
            .background(Theme.paper)
            if drawer {
                Color.black.opacity(0.25).ignoresSafeArea().onTapGesture { withAnimation(.easeIn(duration: 0.18)) { drawer = false } }
                Sidebar(onClose: { withAnimation(.easeIn(duration: 0.18)) { drawer = false } }, onSettings: { drawer = false; settings = true })
                    .transition(.move(edge: .leading))
            }
        }
        .sheet(isPresented: $settings) { SettingsView() }
        .sheet(isPresented: Binding(get: { store.pendingConfirm != nil }, set: { if !$0 { store.answerConfirm(false) } })) {
            ConfirmSheet()
        }
        .alert("Could not reach your Mac", isPresented: Binding(get: { store.error != nil }, set: { if !$0 { store.error = nil } })) {
            Button("OK") { store.error = nil }
        } message: { Text(store.error ?? "") }
    }
}

/// Her mark and her name for a second while the app comes up.
struct Splash: View {
    var body: some View {
        VStack(spacing: 14) {
            Mark(size: 112)
            Text("Samantha").font(.system(size: 30, weight: .semibold))
            Text("Runs on this phone.").font(.subheadline).foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Theme.paper)
        .ignoresSafeArea()
        .accessibilityIdentifier("splash")
    }
}

/// Drops the keyboard before a drawer or a sheet covers it.
func hideKeyboard() {
    #if os(iOS)
    UIApplication.shared.sendAction(#selector(UIResponder.resignFirstResponder), to: nil, from: nil, for: nil)
    #endif
}

struct TopBar: View {
    var onMenu: () -> Void
    var onNew: () -> Void

    var body: some View {
        HStack {
            Button(action: onMenu) { Image(systemName: "line.3.horizontal").font(.system(size: 18, weight: .medium)) }
                .accessibilityLabel("Chats")
            Spacer()
            Text("Samantha").font(Theme.title)
            Spacer()
            Button(action: onNew) { Image(systemName: "square.and.pencil").font(.system(size: 18, weight: .medium)) }
                .accessibilityLabel("New chat")
        }
        .foregroundStyle(Theme.ink)
        .padding(.horizontal, 16)
        .frame(height: 48)
        .background(Theme.paper)
    }
}

struct HomeView: View {
    @Environment(Store.self) private var store
    private var greeting: String {
        let hour = Calendar.current.component(.hour, from: Date())
        switch hour {
        case 5..<12: return "Good morning"
        case 12..<17: return "Good afternoon"
        default: return "Good evening"
        }
    }

    var body: some View {
        VStack(spacing: 14) {
            Spacer()
            Mark(size: 72)
            Text(greeting).font(Theme.greeting).foregroundStyle(Theme.ink)
            Text(store.model.isReady ? "Ask me anything. I run on this phone." : "Ask me anything. My exact tools work now; download my models in Settings for the rest.")
                .font(Theme.body).foregroundStyle(Theme.muted).multilineTextAlignment(.center)
            Spacer()
            Spacer()
        }
        .frame(maxWidth: .infinity)
        .padding(.horizontal, 24)
    }
}

/// A pill at the bottom that grows with the text: plus on the left, send on the right.
struct Composer: View {
    @Environment(Store.self) private var store
    @State private var text = ""
    @FocusState private var focused: Bool
    private var voice = Voice.shared

    var body: some View {
        HStack(alignment: .bottom, spacing: 8) {
            // No plus button until it does something (attachments come with her eyes); a dead control is worse than none.
            TextField("Ask Samantha", text: $text, axis: .vertical)
                .font(Theme.body)
                .lineLimit(1...6)
                .focused($focused)
                .foregroundStyle(Theme.ink)
                .frame(minHeight: 36)
                .onSubmit(send)
            if text.trimmingCharacters(in: .whitespaces).isEmpty || voice.listening {
                // Mic: tap to talk, tap again to send what she heard. Her answer is read back to you.
                Button(action: talk) {
                    Image(systemName: voice.listening ? "stop.fill" : "mic").font(.system(size: 16, weight: .semibold))
                        .foregroundStyle(voice.listening ? Theme.paper : Theme.ink)
                        .frame(width: 32, height: 32).background(voice.listening ? Theme.ink : Color.clear).clipShape(Circle())
                }
                .disabled(store.busy)
                .accessibilityLabel(voice.listening ? "Stop and send" : "Talk")
            } else {
                Button(action: send) {
                    Image(systemName: "arrow.up").font(.system(size: 16, weight: .bold)).foregroundStyle(.white)
                        .frame(width: 32, height: 32).background(Theme.accent).clipShape(Circle())
                }
                .opacity(store.busy ? 0.4 : 1)
                .disabled(store.busy)
                .accessibilityLabel("Send")
            }
        }
        .padding(.leading, 6).padding(.trailing, 8).padding(.vertical, 6)
        .background(Theme.field)
        .overlay(RoundedRectangle(cornerRadius: 24, style: .continuous).stroke(Theme.line, lineWidth: 1))
        .clipShape(RoundedRectangle(cornerRadius: 24, style: .continuous))
        .padding(.horizontal, 12).padding(.bottom, 8).padding(.top, 6)
        .background(Theme.paper)
        .onChange(of: voice.heard) { _, heard in if voice.listening { text = heard } }
        .onChange(of: text) { _, _ in if !voice.listening { voice.problem = nil } }
        .overlay(alignment: .top) {
            if let p = voice.problem { Text(p).font(Theme.small).foregroundStyle(Theme.muted).offset(y: -18) }
        }
    }

    private func talk() {
        if voice.listening {
            let line = voice.stop()
            text = ""
            store.send(line, byVoice: true)
        } else {
            focused = false
            voice.start()
        }
    }

    private func send() {
        let line = text
        text = ""
        store.send(line)
    }
}
