import type { Metadata } from "next";
import { Inter, Source_Serif_4 } from "next/font/google";

import { AuthProvider } from "@/lib/auth";
import "./globals.css";

// next/font self-hosts these at build time, so there is no request to Google at runtime and
// DEMO_MODE stays genuinely offline. Source Serif 4 was drawn for screen reading and holds
// up in print; Inter carries the data, where legibility on an old monitor matters more than
// character.
const serif = Source_Serif_4({
  subsets: ["latin"], display: "swap", variable: "--font-serif",
  weight: ["400", "600", "700"],
});
const sans = Inter({
  subsets: ["latin"], display: "swap", variable: "--font-sans",
});

export const metadata: Metadata = {
  title: "PRAMAAN — DPR Appraisal",
  description:
    "Detailed Project Report quality assessment and risk prediction. Advisory only.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${serif.variable} ${sans.variable}`}>
      <body suppressHydrationWarning>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
