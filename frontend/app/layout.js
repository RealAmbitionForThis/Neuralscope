import "./globals.css";

import AppShell from "@/components/layout/AppShell";

export const metadata = {
  title: "NeuralScope",
  description:
    "Visualize LLM internals, identify refusal behaviors, and surgically modify weights.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
