import { Analytics } from "@vercel/analytics/next";
import type { Metadata } from "next";
import { IBM_Plex_Mono, IBM_Plex_Sans } from "next/font/google";
import { SimulatedTutorBanner } from "@/components/SimulatedTutorBanner";
import Link from "next/link";
import "./globals.css";

const sans = IBM_Plex_Sans({ subsets: ["latin"], weight: ["400", "500", "600"], variable: "--font-plex-sans" });
const mono = IBM_Plex_Mono({ subsets: ["latin"], weight: ["400", "500"], variable: "--font-plex-mono" });

export const metadata: Metadata = {
  title: "RMN Tutor",
  description: "Tutor de interpretação de espectros de RMN de ¹H",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" className={`${sans.variable} ${mono.variable}`}>
      <body className="min-h-screen font-sans antialiased">
        <header className="border-b border-line bg-card/80">
          <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
            <Link href="/" className="text-lg font-semibold tracking-tight">
              RMN <span className="text-accent">Tutor</span>
            </Link>
            <nav className="flex gap-4 text-sm text-muted">
              <Link href="/">Início</Link>
              <Link href="/sessoes/nova">Novo espectro</Link>
            </nav>
          </div>
        </header>
        <SimulatedTutorBanner />
        <main className="mx-auto max-w-7xl px-4 py-6">{children}</main>
        <Analytics />
      </body>
    </html>
  );
}
