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
  static let light = NSColor(hex: 0xFFF9EC)
  static let ink = NSColor(hex: 0x111827)
}

private enum IdleAshesBrand {
  static let name = "Idle Ashes"
  static let charcoalHex = "#2B2A25"
  static let ashHex = "#7C756B"
  static let ivoryHex = "#F4EEE6"
  static let clayHex = "#A66036"
  static let emberHex = "#C1784A"
  static let panelHex = "#E9DFD2"
  static let inkHex = "#24231F"

  static let charcoal = NSColor(hex: 0x2B2A25)
  static let ash = NSColor(hex: 0x7C756B)
  static let ivory = NSColor(hex: 0xF4EEE6)
  static let clay = NSColor(hex: 0xA66036)
  static let ember = NSColor(hex: 0xC1784A)
  static let panel = NSColor(hex: 0xE9DFD2)
  static let ink = NSColor(hex: 0x24231F)
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

private func drawRadiantBackground(width: CGFloat, height: CGFloat, center: NSPoint) {
  let bounds = NSRect(x: 0, y: 0, width: width, height: height)
  Brand.ivory.setFill()
  bounds.fill()

  if let glow = NSGradient(
    colorsAndLocations:
      (NSColor.white.withAlphaComponent(0.96), 0),
      (Brand.light.withAlphaComponent(0.78), 0.18),
      (Brand.ivory.withAlphaComponent(0.82), 0.54),
      (NSColor(hex: 0xEDEAE5).withAlphaComponent(1), 1)
  ) {
    glow.draw(
      fromCenter: center,
      radius: 0,
      toCenter: center,
      radius: max(width, height) * 0.78,
      options: []
    )
  }

  let rayColor = NSColor.white.withAlphaComponent(0.44)
  for angle in stride(from: -28.0, through: 208.0, by: 28.0) {
    let radians = CGFloat(angle * .pi / 180)
    let end = NSPoint(
      x: center.x + cos(radians) * max(width, height),
      y: center.y + sin(radians) * max(width, height)
    )
    drawLine(
      from: center,
      to: end,
      color: rayColor,
      width: angle.truncatingRemainder(dividingBy: 56) == 0 ? 2.2 : 1.2,
      cap: .butt
    )
  }

  drawLine(
    from: NSPoint(x: 0, y: center.y + 52),
    to: NSPoint(x: width, y: center.y + 52),
    color: NSColor.white.withAlphaComponent(0.56),
    width: 2,
    cap: .butt
  )
  drawLine(
    from: NSPoint(x: center.x, y: 0),
    to: NSPoint(x: center.x, y: height),
    color: NSColor.white.withAlphaComponent(0.30),
    width: 6,
    cap: .butt
  )
}

private func drawSoftIconBackground(width: CGFloat, height: CGFloat) {
  let bounds = NSRect(x: 0, y: 0, width: width, height: height)
  Brand.ivory.setFill()
  bounds.fill()

  if let glow = NSGradient(
    colorsAndLocations:
      (NSColor.white.withAlphaComponent(0.92), 0),
      (Brand.light.withAlphaComponent(0.72), 0.26),
      (Brand.ivory.withAlphaComponent(1), 1)
  ) {
    glow.draw(
      fromCenter: NSPoint(x: width * 0.5, y: height * 0.42),
      radius: 0,
      toCenter: NSPoint(x: width * 0.5, y: height * 0.42),
      radius: max(width, height) * 0.68,
      options: []
    )
  }
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
    (34, 116, 140),
    (47, 104, 152),
    (60, 88, 168),
    (74, 72, 184),
    (88, 58, 198),
    (102, 72, 184),
    (116, 88, 168),
    (130, 104, 152),
  ]

  for bar in bars {
    drawLine(
      from: point(bar.x, bar.top, origin, scale),
      to: point(bar.x, bar.bottom, origin, scale),
      color: markColor,
      width: 6.7 * scale
    )
  }

  let leftPage = NSBezierPath()
  leftPage.move(to: point(166, 48, origin, scale))
  leftPage.line(to: point(166, 174, origin, scale))
  leftPage.curve(
    to: point(132, 190, origin, scale),
    controlPoint1: point(154, 174, origin, scale),
    controlPoint2: point(142, 180, origin, scale)
  )
  leftPage.curve(
    to: point(132, 78, origin, scale),
    controlPoint1: point(128, 156, origin, scale),
    controlPoint2: point(128, 112, origin, scale)
  )
  leftPage.curve(
    to: point(166, 48, origin, scale),
    controlPoint1: point(142, 62, origin, scale),
    controlPoint2: point(154, 52, origin, scale)
  )
  leftPage.close()
  markColor.setFill()
  leftPage.fill()

  let rightPage = NSBezierPath()
  rightPage.lineWidth = 5.8 * scale
  rightPage.lineJoinStyle = .round
  rightPage.lineCapStyle = .round
  rightPage.move(to: point(181, 66, origin, scale))
  rightPage.curve(
    to: point(224, 82, origin, scale),
    controlPoint1: point(197, 64, origin, scale),
    controlPoint2: point(213, 70, origin, scale)
  )
  rightPage.line(to: point(224, 180, origin, scale))
  rightPage.curve(
    to: point(181, 166, origin, scale),
    controlPoint1: point(212, 170, origin, scale),
    controlPoint2: point(196, 164, origin, scale)
  )
  markColor.setStroke()
  rightPage.stroke()

  drawLine(
    from: point(174, 58, origin, scale),
    to: point(174, 178, origin, scale),
    color: markColor,
    width: 5.7 * scale
  )

  drawLine(
    from: point(196, 76, origin, scale),
    to: point(196, 168, origin, scale),
    color: markColor,
    width: 4.2 * scale
  )

  drawLine(
    from: point(209, 82, origin, scale),
    to: point(209, 172, origin, scale),
    color: markColor,
    width: 3.8 * scale
  )

  if includeAccent {
    let accent = NSBezierPath()
    accent.lineWidth = 4.4 * scale
    accent.lineCapStyle = .round
    accent.move(to: point(132, 198, origin, scale))
    accent.curve(
      to: point(224, 198, origin, scale),
      controlPoint1: point(160, 210, origin, scale),
      controlPoint2: point(196, 210, origin, scale)
    )
    accentColor.setStroke()
    accent.stroke()
  }
}

private func drawIdleAshesMark(
  in rect: NSRect,
  markColor: NSColor = IdleAshesBrand.charcoal,
  accentColor: NSColor = IdleAshesBrand.ember,
  includeAccent: Bool = true
) {
  let side = min(rect.width, rect.height)
  let scale = side / 256
  let origin = NSPoint(x: rect.midX - side / 2, y: rect.midY - side / 2)

  func path(_ points: [(CGFloat, CGFloat)], close: Bool = true) -> NSBezierPath {
    let p = NSBezierPath()
    p.move(to: point(points[0].0, points[0].1, origin, scale))
    for item in points.dropFirst() {
      p.line(to: point(item.0, item.1, origin, scale))
    }
    if close { p.close() }
    return p
  }

  let fragments: [[(CGFloat, CGFloat)]] = [
    [(123, 22), (149, 44), (139, 76), (109, 82), (91, 56), (101, 31)],
    [(73, 82), (101, 100), (94, 132), (63, 142), (44, 117), (50, 91)],
    [(157, 84), (188, 98), (194, 132), (169, 154), (139, 143), (134, 111)],
    [(96, 151), (132, 142), (157, 166), (145, 199), (108, 207), (82, 184)],
    [(154, 170), (190, 159), (211, 184), (199, 219), (162, 229), (137, 204)],
  ]

  for (index, fragment) in fragments.enumerated() {
    let alpha = index == 0 ? 0.34 : 1
    markColor.withAlphaComponent(alpha).setFill()
    path(fragment).fill()
  }

  if includeAccent {
    let ember = NSBezierPath(ovalIn: NSRect(
      x: origin.x + 117 * scale,
      y: origin.y + 136 * scale,
      width: 24 * scale,
      height: 24 * scale
    ))
    accentColor.setFill()
    ember.fill()
  }
}

private func drawIdleAshesWordmark(canvasWidth: CGFloat, topY: CGFloat, size: CGFloat) {
  _ = drawCenteredText(
    "idle ashes",
    y: topY,
    size: size,
    color: IdleAshesBrand.ink,
    canvasWidth: canvasWidth
  )
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
    drawSoftIconBackground(width: 1024, height: 1024)
    Brand.parchment.withAlphaComponent(0.36).setFill()
    NSBezierPath(ovalIn: NSRect(x: 198, y: 188, width: 628, height: 628)).fill()
    drawBrandMark(in: NSRect(x: 218, y: 228, width: 588, height: 588))
  }
  try flattenOpaquePNG(at: appIconURL, background: Brand.ivory)

  try writePNG(width: 1024, height: 1024, background: Brand.ivory, hasAlpha: false, to: splashURL) {
    drawRadiantBackground(width: 1024, height: 1024, center: NSPoint(x: 512, y: 238))
    drawBrandMark(in: NSRect(x: 386, y: 148, width: 252, height: 252))
    drawWordmark(canvasWidth: 1024, topY: 318, large: true)
  }
  try flattenOpaquePNG(at: splashURL, background: Brand.ivory)

  try writePNG(width: 48, height: 48, background: Brand.ivory, hasAlpha: false, to: faviconURL) {
    drawBrandMark(in: NSRect(x: 6, y: 6, width: 36, height: 36), includeAccent: false)
  }
  try flattenOpaquePNG(at: faviconURL, background: Brand.ivory)

  try writePNG(width: 512, height: 512, background: Brand.ivory, hasAlpha: false, to: androidBackgroundURL) {}
  try flattenOpaquePNG(at: androidBackgroundURL, background: Brand.ivory)

  try writePNG(width: 512, height: 512, background: nil, to: imageURL.appendingPathComponent("android-icon-foreground.png")) {
    drawBrandMark(in: NSRect(x: 98, y: 98, width: 316, height: 316))
  }

  try writePNG(width: 432, height: 432, background: nil, to: imageURL.appendingPathComponent("android-icon-monochrome.png")) {
    drawBrandMark(in: NSRect(x: 58, y: 58, width: 316, height: 316), markColor: Brand.ink, accentColor: Brand.ink, includeAccent: false)
  }

  try writePNG(width: 512, height: 512, background: nil, to: brandURL.appendingPathComponent("freely-spoken-mark.png")) {
    drawBrandMark(in: NSRect(x: 58, y: 58, width: 396, height: 396))
  }

  try writePNG(width: 1366, height: 768, background: Brand.ivory, hasAlpha: false, to: brandURL.appendingPathComponent("freely-spoken-lockup.png")) {
    drawRadiantBackground(width: 1366, height: 768, center: NSPoint(x: 683, y: 154))
    drawBrandMark(in: NSRect(x: 555, y: 112, width: 256, height: 256))
    drawWordmark(canvasWidth: 1366, topY: 286, large: true)
  }
  try flattenOpaquePNG(at: brandURL.appendingPathComponent("freely-spoken-lockup.png"), background: Brand.ivory)

  try writePNG(width: 1200, height: 420, background: nil, to: brandURL.appendingPathComponent("freely-spoken-wordmark.png")) {
    drawWordmark(canvasWidth: 1200, topY: 30, large: true)
  }

  try writeIdleAshesRasterAssets()
}

private func writeIdleAshesRasterAssets() throws {
  let iconURL = imageURL.appendingPathComponent("idle-ashes-icon.png")
  let splashURL = imageURL.appendingPathComponent("idle-ashes-splash-icon.png")
  let faviconURL = imageURL.appendingPathComponent("idle-ashes-favicon.png")
  let androidBackgroundURL = imageURL.appendingPathComponent("idle-ashes-android-icon-background.png")

  try writePNG(width: 1024, height: 1024, background: IdleAshesBrand.ivory, hasAlpha: false, to: iconURL) {
    IdleAshesBrand.ivory.setFill()
    NSRect(x: 0, y: 0, width: 1024, height: 1024).fill()
    IdleAshesBrand.panel.withAlphaComponent(0.45).setFill()
    NSBezierPath(ovalIn: NSRect(x: 198, y: 188, width: 628, height: 628)).fill()
    drawIdleAshesMark(in: NSRect(x: 246, y: 180, width: 532, height: 532))
  }
  try flattenOpaquePNG(at: iconURL, background: IdleAshesBrand.ivory)

  try writePNG(width: 1024, height: 1024, background: IdleAshesBrand.ivory, hasAlpha: false, to: splashURL) {
    IdleAshesBrand.ivory.setFill()
    NSRect(x: 0, y: 0, width: 1024, height: 1024).fill()
    drawIdleAshesMark(in: NSRect(x: 386, y: 170, width: 252, height: 252))
    drawIdleAshesWordmark(canvasWidth: 1024, topY: 442, size: 132)
  }
  try flattenOpaquePNG(at: splashURL, background: IdleAshesBrand.ivory)

  try writePNG(width: 48, height: 48, background: IdleAshesBrand.ivory, hasAlpha: false, to: faviconURL) {
    drawIdleAshesMark(in: NSRect(x: 6, y: 6, width: 36, height: 36), includeAccent: false)
  }
  try flattenOpaquePNG(at: faviconURL, background: IdleAshesBrand.ivory)

  try writePNG(width: 512, height: 512, background: IdleAshesBrand.ivory, hasAlpha: false, to: androidBackgroundURL) {}
  try flattenOpaquePNG(at: androidBackgroundURL, background: IdleAshesBrand.ivory)

  try writePNG(width: 512, height: 512, background: nil, to: imageURL.appendingPathComponent("idle-ashes-android-icon-foreground.png")) {
    drawIdleAshesMark(in: NSRect(x: 98, y: 98, width: 316, height: 316))
  }

  try writePNG(width: 432, height: 432, background: nil, to: imageURL.appendingPathComponent("idle-ashes-android-icon-monochrome.png")) {
    drawIdleAshesMark(in: NSRect(x: 58, y: 58, width: 316, height: 316), markColor: IdleAshesBrand.ink, accentColor: IdleAshesBrand.ink, includeAccent: false)
  }

  try writePNG(width: 512, height: 512, background: nil, to: brandURL.appendingPathComponent("idle-ashes-mark.png")) {
    drawIdleAshesMark(in: NSRect(x: 58, y: 58, width: 396, height: 396))
  }

  try writePNG(width: 1366, height: 768, background: IdleAshesBrand.ivory, hasAlpha: false, to: brandURL.appendingPathComponent("idle-ashes-lockup.png")) {
    IdleAshesBrand.ivory.setFill()
    NSRect(x: 0, y: 0, width: 1366, height: 768).fill()
    drawIdleAshesMark(in: NSRect(x: 555, y: 132, width: 256, height: 256))
    drawIdleAshesWordmark(canvasWidth: 1366, topY: 440, size: 150)
  }
  try flattenOpaquePNG(at: brandURL.appendingPathComponent("idle-ashes-lockup.png"), background: IdleAshesBrand.ivory)

  try writePNG(width: 1200, height: 420, background: nil, to: brandURL.appendingPathComponent("idle-ashes-wordmark.png")) {
    drawIdleAshesWordmark(canvasWidth: 1200, topY: 120, size: 150)
  }
}

private func markSVG() -> String {
  let navy = Brand.navyHex
  let gold = Brand.goldHex
  return """
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" role="img" aria-labelledby="title">
    <title id="title">Freely Spoken mark</title>
    <g fill="none" stroke="\(navy)" stroke-linecap="round" stroke-linejoin="round">
      <path d="M34 116v24" stroke-width="6.7"/>
      <path d="M47 104v48" stroke-width="6.7"/>
      <path d="M60 88v80" stroke-width="6.7"/>
      <path d="M74 72v112" stroke-width="6.7"/>
      <path d="M88 58v140" stroke-width="6.7"/>
      <path d="M102 72v112" stroke-width="6.7"/>
      <path d="M116 88v80" stroke-width="6.7"/>
      <path d="M130 104v48" stroke-width="6.7"/>
    </g>
    <path fill="\(navy)" d="M166 48v126c-12 0-24 6-34 16-4-34-4-78 0-112 10-16 22-26 34-30Z"/>
    <g fill="none" stroke="\(navy)" stroke-linecap="round" stroke-linejoin="round">
      <path d="M181 66c16-2 32 4 43 16v98c-12-10-28-16-43-14" stroke-width="5.8"/>
      <path d="M174 58v120" stroke-width="5.7"/>
      <path d="M196 76v92" stroke-width="4.2"/>
      <path d="M209 82v90" stroke-width="3.8"/>
    </g>
    <path d="M132 198c28 12 64 12 92 0" fill="none" stroke="\(gold)" stroke-width="4.4" stroke-linecap="round"/>
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
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1366 768" role="img" aria-labelledby="title">
    <title id="title">Freely Spoken logo lockup</title>
    <defs>
      <radialGradient id="glow" cx="50%" cy="20%" r="78%">
        <stop offset="0%" stop-color="#FFFFFF"/>
        <stop offset="20%" stop-color="#FFF9EC"/>
        <stop offset="60%" stop-color="#F7F1E8"/>
        <stop offset="100%" stop-color="#EDEAE5"/>
      </radialGradient>
    </defs>
    <rect width="1366" height="768" fill="#F7F1E8"/>
    <rect width="1366" height="768" fill="url(#glow)"/>
    <g stroke="#FFFFFF" stroke-linecap="butt" opacity="0.55">
      <path d="M683 154H1366" stroke-width="2"/>
      <path d="M0 206H1366" stroke-width="2"/>
      <path d="M683 0V768" stroke-width="5" opacity="0.45"/>
      <path d="M683 154 0 0" stroke-width="1.2"/>
      <path d="M683 154 1366 0" stroke-width="1.2"/>
      <path d="M683 154 0 724" stroke-width="1.2"/>
      <path d="M683 154 1366 724" stroke-width="1.2"/>
    </g>
    <g transform="translate(555 112)">
  \(markSVG().replacingOccurrences(of: "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 256 256\" role=\"img\" aria-labelledby=\"title\">\n  <title id=\"title\">Freely Spoken mark</title>\n", with: "").replacingOccurrences(of: "\n</svg>", with: ""))
    </g>
    <text x="683" y="420" text-anchor="middle" fill="\(Brand.goldHex)" font-family="Georgia, 'Times New Roman', serif" font-size="150" font-weight="700">Freely</text>
    <text x="683" y="588" text-anchor="middle" fill="\(Brand.navyHex)" font-family="Georgia, 'Times New Roman', serif" font-size="172" font-weight="700">Spoken</text>
  </svg>
  """
}

private func idleAshesMarkSVG() -> String {
  let charcoal = IdleAshesBrand.charcoalHex
  let ember = IdleAshesBrand.emberHex
  return """
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" role="img" aria-labelledby="title">
    <title id="title">Idle Ashes mark</title>
    <g fill="\(charcoal)">
      <path opacity="0.34" d="M123 22 149 44 139 76 109 82 91 56 101 31Z"/>
      <path d="M73 82 101 100 94 132 63 142 44 117 50 91Z"/>
      <path d="M157 84 188 98 194 132 169 154 139 143 134 111Z"/>
      <path d="M96 151 132 142 157 166 145 199 108 207 82 184Z"/>
      <path d="M154 170 190 159 211 184 199 219 162 229 137 204Z"/>
    </g>
    <circle cx="129" cy="148" r="12" fill="\(ember)"/>
  </svg>
  """
}

private func idleAshesWordmarkSVG() -> String {
  """
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 240" role="img" aria-labelledby="title">
    <title id="title">Idle Ashes wordmark</title>
    <text x="450" y="160" text-anchor="middle" fill="\(IdleAshesBrand.inkHex)" font-family="Georgia, 'Times New Roman', serif" font-size="150" font-weight="700">idle ashes</text>
  </svg>
  """
}

private func idleAshesLockupSVG() -> String {
  """
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1366 768" role="img" aria-labelledby="title">
    <title id="title">Idle Ashes logo lockup</title>
    <rect width="1366" height="768" fill="\(IdleAshesBrand.ivoryHex)"/>
    <g transform="translate(555 132)">
  \(idleAshesMarkSVG().replacingOccurrences(of: "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 256 256\" role=\"img\" aria-labelledby=\"title\">\n  <title id=\"title\">Idle Ashes mark</title>\n", with: "").replacingOccurrences(of: "\n</svg>", with: ""))
    </g>
    <text x="683" y="540" text-anchor="middle" fill="\(IdleAshesBrand.inkHex)" font-family="Georgia, 'Times New Roman', serif" font-size="150" font-weight="700">idle ashes</text>
  </svg>
  """
}

private func writeSVGAssets() throws {
  try writeText(markSVG(), to: brandURL.appendingPathComponent("freely-spoken-mark.svg"))
  try writeText(wordmarkSVG(), to: brandURL.appendingPathComponent("freely-spoken-wordmark.svg"))
  try writeText(lockupSVG(), to: brandURL.appendingPathComponent("freely-spoken-lockup.svg"))
  try writeText(idleAshesMarkSVG(), to: brandURL.appendingPathComponent("idle-ashes-mark.svg"))
  try writeText(idleAshesWordmarkSVG(), to: brandURL.appendingPathComponent("idle-ashes-wordmark.svg"))
  try writeText(idleAshesLockupSVG(), to: brandURL.appendingPathComponent("idle-ashes-lockup.svg"))
}

private func writeReadme() throws {
  let readme = """
  # Freely Spoken Brand Assets

  Generated by `tools/branding/generate-freely-spoken-assets.swift`.

  ## Core Identity

  - Product name: Freely Spoken
  - Mark: waveform plus open book
  - Voice: calm, direct, reflective
  - Splash and lockup treatment: warm radiant field inspired by the original brand direction

  ## Colors

  - Brand navy: `#172235`
  - Brand gold: `#B18A55`
  - Brand ivory: `#F7F1E8`
  - Brand parchment: `#EFE4D3`
  - Ink: `#111827`

  ## Files

  - `freely-spoken-mark.svg` / `freely-spoken-mark.png`
  - `freely-spoken-wordmark.svg` / `freely-spoken-wordmark.png`
  - `freely-spoken-lockup.svg` / `freely-spoken-lockup.png` - wide radiant brand lockup
  - Expo assets in `assets/images/`: app icon, splash icon, favicon, and adaptive icon images.

  ## Idle Ashes

  - Product name: Idle Ashes
  - Mark: abstract cooling ash fragments with restrained ember point
  - Voice: quiet, private, reflective, literate
  - Palette: charcoal, ash gray, warm ivory, clay, copper ember

  ### Colors

  - Charcoal: `#2B2A25`
  - Ash gray: `#7C756B`
  - Ivory: `#F4EEE6`
  - Clay: `#A66036`
  - Copper ember: `#C1784A`
  - Panel: `#E9DFD2`
  - Ink: `#24231F`

  ### Files

  - `idle-ashes-mark.svg` / `idle-ashes-mark.png`
  - `idle-ashes-wordmark.svg` / `idle-ashes-wordmark.png`
  - `idle-ashes-lockup.svg` / `idle-ashes-lockup.png`
  - Expo assets in `assets/images/idle-ashes-*`

  Keep generated assets in sync by editing the generator and rerunning it from the repository root.
  """

  try writeText(readme, to: brandURL.appendingPathComponent("README.md"))
}

try ensureDirectories()
try writeRasterAssets()
try writeSVGAssets()
try writeReadme()
print("Generated Freely Spoken brand assets.")
