// Throwaway: walks the app with the mock Samantha and saves a screenshot of every screen for grading.
// Run: xcodebuild test -scheme Samantha -destination 'id=<sim udid>' -only-testing:SamanthaUITests/Shots
// TEST_RUNNER_SHOTS_DIR names the folder, TEST_RUNNER_SHOTS_PREFIX the file prefix (light, dark).
import XCTest

final class Shots: XCTestCase {
    private var dir: URL { URL(fileURLWithPath: ProcessInfo.processInfo.environment["SHOTS_DIR"] ?? "/tmp") }
    private var prefix: String { ProcessInfo.processInfo.environment["SHOTS_PREFIX"] ?? "shot" }

    private func shot(_ name: String) {
        let png = XCUIScreen.main.screenshot().pngRepresentation
        try? png.write(to: dir.appendingPathComponent("\(prefix)-\(name).png"))
    }

    func testEveryScreen() throws {
        let app = XCUIApplication()
        app.launchArguments = ["--mock"]
        app.launch()
        shot("splash")
        sleep(2)
        shot("home")

        let field = app.textViews.firstMatch.exists ? app.textViews.firstMatch : app.textFields.firstMatch
        field.tap()
        field.typeText("what time is it in tokyo")
        shot("typing")
        app.buttons["Send"].tap()
        sleep(1)
        shot("working")
        sleep(2)
        shot("chat")

        // A run of her exact tools (answered on the phone) and one plain question (the stand-in Mac answers it).
        for (i, q) in ["flip 3 coins", "what's 15% of 240", "how many days until christmas", "convert 5 miles to km",
                       "reverse the word samantha", "write a haiku about rain"].enumerated() {
            field.tap()
            field.typeText(q)
            app.buttons["Send"].tap()
            sleep(2)
            shot("q\(i + 1)")
        }

        app.buttons["Chats"].tap()
        sleep(1)
        shot("drawer")
        app.buttons["Close"].tap()
        sleep(1)

        field.tap()
        field.typeText("delete old.zip")
        app.buttons["Send"].tap()
        sleep(2)
        shot("confirm")
        if app.buttons["No"].exists { app.buttons["No"].tap() }
        sleep(1)

        app.buttons["Chats"].tap()
        sleep(1)
        let pair = app.buttons.matching(NSPredicate(format: "label CONTAINS 'Pair' OR label CONTAINS 'Mac'")).firstMatch
        if pair.exists { pair.tap() }
        sleep(1)
        shot("settings")
    }
}
