import type { Metadata } from "next";
import "@fontsource/ubuntu/400.css";
import "@fontsource/ubuntu/500.css";
import "@fontsource/ubuntu/700.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "KYCX — Adverse Media Check",
  description: "Evidence-first adverse media checks with identity verification",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
