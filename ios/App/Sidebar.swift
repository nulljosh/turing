// The drawer: past chats, newest first, and the way to Settings.
import SwiftUI

struct Sidebar: View {
    @Environment(Store.self) private var store
    var onClose: () -> Void
    var onSettings: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                Mark(size: 28)
                Text("Samantha").font(Theme.title).foregroundStyle(Theme.ink)
                Spacer()
                Button(action: onClose) { Image(systemName: "xmark").font(.system(size: 15, weight: .medium)).foregroundStyle(Theme.muted) }
                    .accessibilityLabel("Close")
            }
            .padding(.horizontal, 16).padding(.top, 12).padding(.bottom, 16)
            Button { store.newChat(); onClose() } label: {
                Label("New chat", systemImage: "square.and.pencil").font(Theme.body).foregroundStyle(Theme.ink)
                    .frame(maxWidth: .infinity, alignment: .leading).padding(.horizontal, 16).padding(.vertical, 10)
            }
            Text("Recents").font(Theme.small).foregroundStyle(Theme.muted).padding(.horizontal, 16).padding(.top, 12).padding(.bottom, 4)
            List {
                ForEach(store.chats) { chat in
                    Button { store.open(chat); onClose() } label: {
                        Text(chat.title).font(Theme.body).foregroundStyle(Theme.ink).lineLimit(1)
                    }
                    .listRowBackground(chat.id == store.current.id ? Theme.bubble : Color.clear)
                }
                .onDelete { idx in idx.map { store.chats[$0] }.forEach { store.delete($0) } }
            }
            .listStyle(.plain)
            .scrollContentBackground(.hidden)
            Divider().overlay(Theme.line)
            Button(action: onSettings) {
                Label(store.pairing.isSet ? store.pairing.host : "Pair with your Mac", systemImage: "desktopcomputer")
                    .font(Theme.body).foregroundStyle(Theme.ink)
                    .frame(maxWidth: .infinity, alignment: .leading).padding(16)
            }
        }
        .frame(width: 300)
        .frame(maxHeight: .infinity)
        .background(Theme.paper)
        .ignoresSafeArea(edges: .bottom)
    }
}

/// Pairing: the Mac's address and the secret from the bridge's terminal line, and a button that pings it.
struct SettingsView: View {
    @Environment(Store.self) private var store
    @Environment(\.dismiss) private var dismiss
    @State private var pairing = Pairing()
    @State private var status = ""

    var body: some View {
        NavigationStack {
            Form {
                Section("Your Mac") {
                    TextField("Host (the Mac's address)", text: $pairing.host).textInputAutocapitalization(.never).autocorrectionDisabled()
                    TextField("Port", value: $pairing.port, format: .number).keyboardType(.numberPad)
                    SecureField("Pairing token", text: $pairing.token)
                }
                Section {
                    Button("Test connection") { test() }.foregroundStyle(Theme.accent)
                    if !status.isEmpty { Text(status).font(Theme.small).foregroundStyle(Theme.muted) }
                } footer: {
                    Text("On the Mac, run app/phone_bridge.py --lan. It prints a samantha://pair link: open it on this phone, or copy the host and token here. Everything stays on your network.")
                }
                Section {
                    Toggle("Rehearse without a Mac", isOn: Binding(get: { store.useMock }, set: { store.useMock = $0 }))
                }
            }
            .scrollContentBackground(.hidden)
            .background(Theme.paper)
            .tint(Theme.accent)
            .navigationTitle("Settings")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) { Button("Done") { pairing.save(); store.pairing = pairing; dismiss() } }
            }
            .onAppear { pairing = store.pairing }
        }
    }

    private func test() {
        status = "Pinging..."
        Task {
            do {
                let v = try await RealClient(pairing: pairing).ping()
                status = "Connected. Samantha \(v) on \(pairing.host)."
            } catch {
                status = error.localizedDescription
            }
        }
    }
}
