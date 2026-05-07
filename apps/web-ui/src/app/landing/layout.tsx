import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  metadataBase: new URL("http://127.0.0.1:3000"),
  title: "Jarvis AI | Self-hosted Turkce AI operasyon katmani",
  description:
    "Jarvis, self-hosted Turkce AI operasyon katmani ile ekipler icin sabit maliyetli bot, onboarding ve gorev yonetimi sunar.",
  alternates: {
    canonical: "/landing"
  },
  openGraph: {
    title: "Jarvis AI | Self-hosted Turkce AI operasyon katmani",
    description:
      "Turkce komut deneyimi, multi-tenant onboarding ve sabit maliyetli AI operasyonu tek panelde yonetin.",
    type: "website",
    url: "/landing",
    images: [
      {
        url: "/jarvis-og.svg",
        width: 1200,
        height: 630,
        alt: "Jarvis AI landing page"
      }
    ]
  },
  twitter: {
    card: "summary_large_image",
    title: "Jarvis AI | Self-hosted Turkce AI operasyon katmani",
    description:
      "Turkce komut deneyimi, multi-tenant onboarding ve sabit maliyetli AI operasyonu tek panelde yonetin.",
    images: ["/jarvis-og.svg"]
  }
};

export default function LandingLayout({ children }: { children: ReactNode }) {
  return children;
}
