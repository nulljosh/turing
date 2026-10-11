// The one screen: a top bar, the home greeting or the conversation, the composer, and the history drawer over it.
import SwiftUI

struct RootView: View {
    @Environment(Store.self) private var store
    @State private var drawer = false
    @State private var settings = false

    var body: some View {
        @Bindable var store = store
        ZStack(alignment: .leading) {
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

/// Drops the keyboard before a drawer or a sheet covers it.
func hideKeyboard() {
    UIApplication.shared.sendAction(#selector(UIResponder.resignFirstResponder), to: nil, from: nil, for: nil)
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
            Text("Ask me anything. I run on this phone.").font(Theme.body).foregroundStyle(Theme.muted)
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

    var body: some View {
        HStack(alignment: .bottom, spacing: 8) {
            Button {} label: { Image(systemName: "plus").font(.system(size: 18, weight: .medium)).foregroundStyle(Theme.ink) }
                .frame(width: 36, height: 36)
                .accessibilityLabel("Add")
            TextField("Ask Samantha", text: $text, axis: .vertical)
                .font(Theme.body)
                .lineLimit(1...6)
                .focused($focused)
                .foregroundStyle(Theme.ink)
                .frame(minHeight: 36)
                .onSubmit(send)
            Button(action: send) {
                Image(systemName: "arrow.up").font(.system(size: 16, weight: .bold)).foregroundStyle(.white)
                    .frame(width: 32, height: 32).background(Theme.accent).clipShape(Circle())
            }
            .opacity(text.trimmingCharacters(in: .whitespaces).isEmpty || store.busy ? 0.4 : 1)
            .disabled(text.trimmingCharacters(in: .whitespaces).isEmpty || store.busy)
            .accessibilityLabel("Send")
        }
        .padding(.leading, 6).padding(.trailing, 8).padding(.vertical, 6)
        .background(Theme.field)
        .overlay(RoundedRectangle(cornerRadius: 24, style: .continuous).stroke(Theme.line, lineWidth: 1))
        .clipShape(RoundedRectangle(cornerRadius: 24, style: .continuous))
        .padding(.horizontal, 12).padding(.bottom, 8).padding(.top, 6)
        .background(Theme.paper)
    }

    private func send() {
        let line = text
        text = ""
        store.send(line)
    }
}
