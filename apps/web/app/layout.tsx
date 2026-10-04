import { IBM_Plex_Mono, Newsreader, Public_Sans } from "next/font/google";
import { SiteFooter, SiteHeader } from "@/components/chrome";
import { DatasetNotice } from "@/components/dataset-notice";
import { canonicalOrigin, siteMetadata } from "@/lib/seo";
import "./globals.css";

const sans = Public_Sans({ subsets: ["latin"], variable: "--font-sans" });
const serif = Newsreader({ subsets: ["latin"], variable: "--font-serif" });
const mono = IBM_Plex_Mono({ subsets: ["latin"], weight: ["400", "500"], variable: "--font-mono" });

export async function generateMetadata() {
  return siteMetadata(canonicalOrigin());
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${sans.variable} ${serif.variable} ${mono.variable}`}>
      <body>
        <a className="skip" href="#content">Skip to content</a>
        <div className="shell">
          <SiteHeader />
          <main id="content" tabIndex={-1}>
            <DatasetNotice />
            {children}
          </main>
          <SiteFooter />
        </div>
      </body>
    </html>
  );
}
