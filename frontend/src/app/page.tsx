import { PublicNav } from "@/components/PublicNav";
import HeroSection from "@/components/landing/HeroSection";
import ExamplesSection from "@/components/landing/ExamplesSection";
import IntegrationsSection from "@/components/landing/IntegrationsSection";
import PricingSection from "@/components/landing/PricingSection";
import FAQSection from "@/components/landing/FAQSection";
import CTASection from "@/components/landing/CTASection";
import FooterSection from "@/components/landing/FooterSection";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background" data-testid="landing-page">
      <PublicNav />
      <HeroSection />
      <ExamplesSection />
      <IntegrationsSection />
      <PricingSection />
      <FAQSection />
      <CTASection />
      <FooterSection />
    </div>
  );
}
