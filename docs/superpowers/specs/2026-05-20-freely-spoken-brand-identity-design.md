# Freely Spoken Brand Identity Design

## Goal

Create a production-ready identity set for the iOS app under the name **Freely Spoken**, based on the approved direction: a clean waveform plus open-book mark, restrained navy and muted gold colors, and a warm ivory brand surface.

## Approved Direction

The production identity should keep the concept from the supplied reference image while removing details that do not survive real app usage. The core logo is a vector-derived mark combining spoken audio and a short sacred passage. The sunburst/glow treatment is not part of the app icon; it is reserved only for future marketing art if needed.

## Asset System

The identity set includes:

- App icon: square 1024px PNG, flat warm ivory background, navy mark, gold accent.
- Standalone mark: SVG and PNG for in-app or documentation usage.
- Wordmark: serif lockup with "Freely" in muted gold and "Spoken" in navy.
- Splash image: centered mark plus wordmark, sized for Expo splash-screen configuration.
- Favicon and Android adaptive icon files: regenerated to avoid stale Expo defaults even though the product is iOS-only.

## Color Tokens

- Brand navy: `#172235`
- Brand gold: `#B18A55`
- Brand ivory: `#F7F1E8`
- Brand parchment: `#EFE4D3`
- Ink: `#111827`
- Muted text: `#6B6257`
- Destructive red: `#B94034`

Dark mode keeps the same brand personality with navy surfaces and ivory text, while preserving red for recording and destructive states.

## App Integration

Update user-facing brand text from `mic-check` to `Freely Spoken` in Expo metadata, permissions copy, and the home-screen title. Keep technical identifiers such as package name, bundle identifier, and slug unchanged unless a future release plan intentionally migrates them.

## Verification

Run asset generation, confirm expected PNG dimensions, and run `npm run lint`. Visual inspection should confirm that the app icon remains legible at small sizes and that the splash image is not carrying background glow or JPEG artifacts.
