#!/usr/bin/env swift

import AppKit
import Foundation
import ImageIO
import UniformTypeIdentifiers

private enum Brand {
  static let name = "Freely Spoken"
  static let navyHex = "#172235"
  static let goldHex = "#B18A55"
  static let ivoryHex = "#F7F1E8"
  static let parchmentHex = "#EFE4D3"
  static let inkHex = "#111827"
  static let navy = NSColor(hex: 0x172235)
  static let gold = NSColor(hex: 0xB18A55)
  static let ivory = NSColor(hex: 0xF7F1E8)
  static let parchment = NSColor(hex: 0xEFE4D3)
  static let ink = NSColor(hex: 0x111827)
}

private extension NSColor {
  convenience init(hex: UInt32, alpha: CGFloat = 1) {
    self.init(
      srgbRed: CGFloat((hex >> 16) & 0xff) / 255,
      green: CGFloat((hex >> 8) & 0xff) / 255,
      blue: CGFloat(hex & 0xff) / 255,
      alpha: alpha
    )
  }
}

private let rootURL = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
private let imageURL = rootURL.appendingPathComponent("assets/images", isDirectory: true)
private let brandURL = rootURL.appendingPathComponent("assets/brand", isDirectory: true)

private func ensureDirectories() throws {
  try FileManager.default.createDirectory(at: imageURL, withIntermediateDirectories: true)
  try FileManager.default.createDirectory(at: brandURL, withIntermediateDirectories: true)
}

private func writeText(_ contents: String, to url: URL) throws {
  try contents.write(to: url, atomically: true, encoding: .utf8)
}

private func writePNG(
  width: CGFloat,
  height: CGFloat,
  background: NSColor?,
  hasAlpha: Bool = true,
  to url: URL,
  draw: () -> Void
) throws {
  let backingScale: CGFloat = NSScreen.main?.backingScaleFactor ?? 2
  let pointWidth = width / backingScale
  let pointHeight = height / backingScale
  let image = NSImage(size: NSSize(width: pointWidth, height: pointHeight))

  image.lockFocusFlipped(true)
  NSGraphicsContext.current?.imageInterpolation = .high

  let transform = NSAffineTransform()
  transform.scaleX(by: 1 / backingScale, yBy: 1 / backingScale)
  transform.concat()

  let canvas = NSRect(x: 0, y: 0, width: width, height: height)
  if let background {
    background.setFill()
    canvas.fill()
  } else if hasAlpha {
    NSColor.clear.setFill()
    canvas.fill(using: .copy)
  }

  draw()
  image.unlockFocus()

  guard
    let tiff = image.tiffRepresentation,
    let bitmap = NSBitmapImageRep(data: tiff),
    let png = bitmap.representation(using: NSBitmapImageRep.FileType.png, properties: [:])
  else {
    throw NSError(domain: "BrandAssetGeneration", code: 1, userInfo: [
      NSLocalizedDescriptionKey: "Could not encode \(url.path) as PNG",
    ])
  }

  _ = hasAlpha

  try png.write(to: url, options: Data.WritingOptions.atomic)
}

private func flattenOpaquePNG(at url: URL, background: NSColor) throws {
  guard
    let source = CGImageSourceCreateWithURL(url as CFURL, nil),
    let sourceImage = CGImageSourceCreateImageAtIndex(source, 0, nil)
  else {
    throw NSError(domain: "BrandAssetGeneration", code: 4, userInfo: [
      NSLocalizedDescriptionKey: "Could not read \(url.path) for flattening",
    ])
  }

  let colorSpace = CGColorSpace(name: CGColorSpace.sRGB) ?? CGColorSpaceCreateDeviceRGB()
  guard let context = CGContext(
    data: nil,
    width: sourceImage.width,
    height: sourceImage.height,
    bitsPerComponent: 8,
    bytesPerRow: 0,
    space: colorSpace,
    bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue
  ) else {
    throw NSError(domain: "BrandAssetGeneration", code: 5, userInfo: [
      NSLocalizedDescriptionKey: "Could not create flattening context for \(url.path)",
    ])
  }

  let rect = CGRect(x: 0, y: 0, width: sourceImage.width, height: sourceImage.height)
  context.setFillColor(background.cgColor)
  context.fill(rect)
  context.draw(sourceImage, in: rect)

  guard
    let flattened = context.makeImage(),
    let destination = CGImageDestinationCreateWithURL(url as CFURL, UTType.png.identifier as CFString, 1, nil)
  else {
    throw NSError(domain: "BrandAssetGeneration", code: 6, userInfo: [
      NSLocalizedDescriptionKey: "Could not create flattened image for \(url.path)",
    ])
  }

  CGImageDestinationAddImage(destination, flattened, nil)
  if !CGImageDestinationFinalize(destination) {
    throw NSError(domain: "BrandAssetGeneration", code: 7, userInfo: [
      NSLocalizedDescriptionKey: "Could not write flattened PNG at \(url.path)",
    ])
  }
}

private func point(_ x: CGFloat, _ y: CGFloat, _ origin: NSPoint, _ scale: CGFloat) -> NSPoint {
  NSPoint(x: origin.x + x * scale, y: origin.y + y * scale)
}

private func drawLine(
  from start: NSPoint,
  to end: NSPoint,
  color: NSColor,
  width: CGFloat,
  cap: NSBezierPath.LineCapStyle = .round
) {
  let path = NSBezierPath()
  path.lineWidth = width
  path.lineCapStyle = cap
  path.move(to: start)
  path.line(to: end)
  color.setStroke()
  path.stroke()
}

private func drawBrandMark(
  in rect: NSRect,
  markColor: NSColor = Brand.navy,
  accentColor: NSColor = Brand.gold,
  includeAccent: Bool = true
) {
  let side = min(rect.width, rect.height)
  let scale = side / 256
  let origin = NSPoint(
    x: rect.midX - side / 2,
    y: rect.midY - side / 2
  )

  let bars: [(x: CGFloat, top: CGFloat, bottom: CGFloat)] = [
    (38, 116, 140),
    (55, 100, 156),
    (72, 82, 174),
    (89, 64, 192),
    (106, 78, 178),
    (123, 96, 160),
  ]

  for bar in bars {
    drawLine(
      from: point(bar.x, bar.top, origin, scale),
      to: point(bar.x, bar.bottom, origin, scale),
      color: markColor,
      width: 8.5 * scale
    )
  }

  let leftPage = NSBezierPath()
  leftPage.move(to: point(154, 56, origin, scale))
  leftPage.line(to: point(154, 176, origin, scale))
  leftPage.curve(
    to: point(92, 190, origin, scale),
    controlPoint1: point(136, 168, origin, scale),
    controlPoint2: point(112, 172, origin, scale)
  )
  leftPage.line(to: point(92, 82, origin, scale))
  leftPage.curve(
    to: point(154, 56, origin, scale),
    controlPoint1: point(112, 66, origin, scale),
    controlPoint2: point(135, 60, origin, scale)
  )
  leftPage.close()
  markColor.setFill()
  leftPage.fill()

  let rightPage = NSBezierPath()
  rightPage.lineWidth = 7.5 * scale
  rightPage.lineJoinStyle = .round
  rightPage.lineCapStyle = .round
  rightPage.move(to: point(168, 68, origin, scale))
  rightPage.curve(
    to: point(213, 84, origin, scale),
    controlPoint1: point(184, 64, origin, scale),
    controlPoint2: point(201, 70, origin, scale)
  )
  rightPage.line(to: point(213, 184, origin, scale))
  rightPage.curve(
    to: point(168, 170, origin, scale),
    controlPoint1: point(199, 174, origin, scale),
    controlPoint2: point(183, 168, origin, scale)
  )
  markColor.setStroke()
  rightPage.stroke()

  drawLine(
    from: point(158, 62, origin, scale),
    to: point(158, 180, origin, scale),
    color: markColor,
    width: 7 * scale
  )

  drawLine(
    from: point(186, 78, origin, scale),
    to: point(186, 174, origin, scale),
    color: markColor,
    width: 5.5 * scale
  )

  if includeAccent {
    let accent = NSBezierPath()
    accent.lineWidth = 5.5 * scale
    accent.lineCapStyle = .round
    accent.move(to: point(94, 200, origin, scale))
    accent.curve(
      to: point(214, 200, origin, scale),
      controlPoint1: point(128, 212, origin, scale),
      controlPoint2: point(180, 212, origin, scale)
    )
    accentColor.setStroke()
    accent.stroke()
  }
}

private func serifFont(size: CGFloat) -> NSFont {
  let names = [
    "Georgia-Bold",
    "TimesNewRomanPS-BoldMT",
    "Times New Roman Bold",
  ]

  for name in names {
    if let font = NSFont(name: name, size: size) {
      return font
    }
  }

  return NSFont.systemFont(ofSize: size, weight: .bold)
}

@discardableResult
private func drawCenteredText(_ text: String, y: CGFloat, size: CGFloat, color: NSColor, canvasWidth: CGFloat) -> CGFloat {
  let attributes: [NSAttributedString.Key: Any] = [
    .font: serifFont(size: size),
    .foregroundColor: color,
  ]
  let attributed = NSAttributedString(string: text, attributes: attributes)
  let measured = attributed.size()
  attributed.draw(at: NSPoint(x: (canvasWidth - measured.width) / 2, y: y))
  return measured.height
}

private func drawWordmark(canvasWidth: CGFloat, topY: CGFloat, large: Bool) {
  let freelySize: CGFloat = large ? 150 : 106
  let spokenSize: CGFloat = large ? 170 : 122
  let freelyHeight = drawCenteredText(
    "Freely",
    y: topY,
    size: freelySize,
    color: Brand.gold,
    canvasWidth: canvasWidth
  )
  _ = drawCenteredText(
    "Spoken",
    y: topY + freelyHeight - (large ? 18 : 12),
    size: spokenSize,
    color: Brand.navy,
    canvasWidth: canvasWidth
  )
}

private func writeRasterAssets() throws {
  let appIconURL = imageURL.appendingPathComponent("icon.png")
  let splashURL = imageURL.appendingPathComponent("splash-icon.png")
  let faviconURL = imageURL.appendingPathComponent("favicon.png")
  let androidBackgroundURL = imageURL.appendingPathComponent("android-icon-background.png")

  try writePNG(width: 1024, height: 1024, background: Brand.ivory, hasAlpha: false, to: appIconURL) {
    Brand.parchment.withAlphaComponent(0.52).setFill()
    NSBezierPath(ovalIn: NSRect(x: 178, y: 168, width: 668, height: 668)).fill()
    drawBrandMark(in: NSRect(x: 210, y: 218, width: 604, height: 604))
  }
  try flattenOpaquePNG(at: appIconURL, background: Brand.ivory)

  try writePNG(width: 1024, height: 1024, background: Brand.ivory, hasAlpha: false, to: splashURL) {
    drawBrandMark(in: NSRect(x: 352, y: 148, width: 320, height: 320))
    drawWordmark(canvasWidth: 1024, topY: 452, large: true)
  }
  try flattenOpaquePNG(at: splashURL, background: Brand.ivory)

  try writePNG(width: 48, height: 48, background: Brand.ivory, hasAlpha: false, to: faviconURL) {
    drawBrandMark(in: NSRect(x: 6, y: 6, width: 36, height: 36), includeAccent: false)
  }
  try flattenOpaquePNG(at: faviconURL, background: Brand.ivory)

  try writePNG(width: 512, height: 512, background: Brand.ivory, hasAlpha: false, to: androidBackgroundURL) {}
  try flattenOpaquePNG(at: androidBackgroundURL, background: Brand.ivory)

  try writePNG(width: 512, height: 512, background: nil, to: imageURL.appendingPathComponent("android-icon-foreground.png")) {
    drawBrandMark(in: NSRect(x: 106, y: 106, width: 300, height: 300))
  }

  try writePNG(width: 432, height: 432, background: nil, to: imageURL.appendingPathComponent("android-icon-monochrome.png")) {
    drawBrandMark(in: NSRect(x: 66, y: 66, width: 300, height: 300), markColor: Brand.ink, accentColor: Brand.ink, includeAccent: false)
  }

  try writePNG(width: 512, height: 512, background: nil, to: brandURL.appendingPathComponent("freely-spoken-mark.png")) {
    drawBrandMark(in: NSRect(x: 56, y: 56, width: 400, height: 400))
  }

  try writePNG(width: 1200, height: 720, background: nil, to: brandURL.appendingPathComponent("freely-spoken-lockup.png")) {
    drawBrandMark(in: NSRect(x: 440, y: 54, width: 320, height: 320))
    drawWordmark(canvasWidth: 1200, topY: 360, large: true)
  }

  try writePNG(width: 1200, height: 420, background: nil, to: brandURL.appendingPathComponent("freely-spoken-wordmark.png")) {
    drawWordmark(canvasWidth: 1200, topY: 30, large: true)
  }
}

private func markSVG() -> String {
  let navy = Brand.navyHex
  let gold = Brand.goldHex
  return """
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" role="img" aria-labelledby="title">
    <title id="title">Freely Spoken mark</title>
    <g fill="none" stroke="\(navy)" stroke-linecap="round" stroke-linejoin="round">
      <path d="M38 116v24" stroke-width="8.5"/>
      <path d="M55 100v56" stroke-width="8.5"/>
      <path d="M72 82v92" stroke-width="8.5"/>
      <path d="M89 64v128" stroke-width="8.5"/>
      <path d="M106 78v100" stroke-width="8.5"/>
      <path d="M123 96v64" stroke-width="8.5"/>
    </g>
    <path fill="\(navy)" d="M154 56v120c-18-8-42-4-62 14V82c20-16 43-22 62-26Z"/>
    <g fill="none" stroke="\(navy)" stroke-linecap="round" stroke-linejoin="round">
      <path d="M168 68c16-4 33 2 45 16v100c-14-10-30-16-45-14" stroke-width="7.5"/>
      <path d="M158 62v118" stroke-width="7"/>
      <path d="M186 78v96" stroke-width="5.5"/>
    </g>
    <path d="M94 200c34 12 86 12 120 0" fill="none" stroke="\(gold)" stroke-width="5.5" stroke-linecap="round"/>
  </svg>
  """
}

private func wordmarkSVG() -> String {
  """
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 330" role="img" aria-labelledby="title">
    <title id="title">Freely Spoken wordmark</title>
    <text x="450" y="126" text-anchor="middle" fill="\(Brand.goldHex)" font-family="Georgia, 'Times New Roman', serif" font-size="142" font-weight="700">Freely</text>
    <text x="450" y="278" text-anchor="middle" fill="\(Brand.navyHex)" font-family="Georgia, 'Times New Roman', serif" font-size="164" font-weight="700">Spoken</text>
  </svg>
  """
}

private func lockupSVG() -> String {
  """
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 650" role="img" aria-labelledby="title">
    <title id="title">Freely Spoken logo lockup</title>
    <g transform="translate(322 24)">
  \(markSVG().replacingOccurrences(of: "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 256 256\" role=\"img\" aria-labelledby=\"title\">\n  <title id=\"title\">Freely Spoken mark</title>\n", with: "").replacingOccurrences(of: "\n</svg>", with: ""))
    </g>
    <text x="450" y="388" text-anchor="middle" fill="\(Brand.goldHex)" font-family="Georgia, 'Times New Roman', serif" font-size="142" font-weight="700">Freely</text>
    <text x="450" y="540" text-anchor="middle" fill="\(Brand.navyHex)" font-family="Georgia, 'Times New Roman', serif" font-size="164" font-weight="700">Spoken</text>
  </svg>
  """
}

private func writeSVGAssets() throws {
  try writeText(markSVG(), to: brandURL.appendingPathComponent("freely-spoken-mark.svg"))
  try writeText(wordmarkSVG(), to: brandURL.appendingPathComponent("freely-spoken-wordmark.svg"))
  try writeText(lockupSVG(), to: brandURL.appendingPathComponent("freely-spoken-lockup.svg"))
}

private func writeReadme() throws {
  let readme = """
  # Freely Spoken Brand Assets

  Generated by `tools/branding/generate-freely-spoken-assets.swift`.

  ## Core Identity

  - Product name: Freely Spoken
  - Mark: waveform plus open book
  - Voice: calm, direct, reflective

  ## Colors

  - Brand navy: `#172235`
  - Brand gold: `#B18A55`
  - Brand ivory: `#F7F1E8`
  - Brand parchment: `#EFE4D3`
  - Ink: `#111827`

  ## Files

  - `freely-spoken-mark.svg` / `freely-spoken-mark.png`
  - `freely-spoken-wordmark.svg` / `freely-spoken-wordmark.png`
  - `freely-spoken-lockup.svg` / `freely-spoken-lockup.png`
  - Expo assets in `assets/images/`: app icon, splash icon, favicon, and adaptive icon images.

  Keep generated assets in sync by editing the generator and rerunning it from the repository root.
  """

  try writeText(readme, to: brandURL.appendingPathComponent("README.md"))
}

try ensureDirectories()
try writeRasterAssets()
try writeSVGAssets()
try writeReadme()
print("Generated Freely Spoken brand assets.")
