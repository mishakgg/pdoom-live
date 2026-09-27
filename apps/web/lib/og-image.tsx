import { ImageResponse } from "next/og";
import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { ogCardLines, type SocialCard } from "@/lib/seo";

export const ogSize = { width: 1200, height: 630 };
export const ogContentType = "image/png";

const fontPath = join(process.cwd(), "assets/fonts/SourceSans3-Regular.ttf");
let fontData: Promise<ArrayBuffer> | null = null;

function loadFont(): Promise<ArrayBuffer> {
  fontData ??= readFile(fontPath).then((bytes) => bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength) as ArrayBuffer);
  return fontData;
}

export async function renderDiscoveryImage(card: SocialCard) {
  const lines = ogCardLines(card);
  const font = await loadFont();
  return new ImageResponse(
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        background: "#f3efe6",
        color: "#1c1915",
        padding: "64px",
        fontFamily: "Source Sans 3",
      }}
    >
      <div style={{ display: "flex", fontSize: 28, letterSpacing: "0.04em" }}>{lines.kicker}</div>
      <div style={{ display: "flex", fontSize: 64, lineHeight: 1.12, marginTop: 28, maxWidth: 1040 }}>{lines.title}</div>
      <div style={{ display: "flex", fontSize: 28, lineHeight: 1.35, marginTop: 32, maxWidth: 1040 }}>{lines.detail}</div>
      <div style={{ display: "flex", marginTop: "auto", fontSize: 32 }}>pdoom.live</div>
    </div>,
    {
      ...ogSize,
      fonts: [{ name: "Source Sans 3", data: font, weight: 400, style: "normal" }],
    },
  );
}
