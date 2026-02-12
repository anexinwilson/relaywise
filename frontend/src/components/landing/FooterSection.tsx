import Link from "next/link";

export default function FooterSection() {
  return (
    <footer className="border-t border-border py-12 px-6" data-testid="footer-section">
      <div className="container mx-auto">
        <div className="flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="flex gap-6 text-sm">
            <a
              href="#how-it-works"
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              How It Works
            </a>
            <Link
              href="/integrations"
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              Integrations
            </Link>
            <Link
              href="/pricing"
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              Pricing
            </Link>
          </div>
          <div className="text-center text-muted-foreground text-sm">
            <p>Built for humans who hate complicated tools</p>
            <p className="text-xs mt-1">Powered by Composio</p>
          </div>
        </div>
      </div>
    </footer>
  );
}
