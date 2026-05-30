// swift-tools-version:6.0
import PackageDescription

let package = Package(
    name: "sentiment-cli",
    platforms: [
        // Foundation Models requires macOS 26 (Tahoe).
        .macOS("26.0"),
    ],
    targets: [
        .executableTarget(
            name: "sentiment-cli",
            path: "Sources/sentiment-cli"
        )
    ]
)
