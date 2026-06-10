// No need to import ThemeProvider here as it's provided in App.tsx
import Navbar from "@/components/Navbar";
import Hero from "@/components/Hero";
import TrustedBy from "@/components/TrustedBy";
import Features from "@/components/Features";
import UseCases from "@/components/UseCases";
import HowItWorks from "@/components/HowItWorks";
import BottomCTA from "@/components/BottomCTA";

const Index = () => {
  return (
    <div className="bg-background min-h-screen font-sans selection:bg-primary/20">
        <Navbar />
        <Hero />
        <TrustedBy />

        <div className="bg-card py-24 border-b border-border">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex flex-col lg:flex-row gap-16 lg:gap-8 justify-between">
              <Features />
              <UseCases />
            </div>
          </div>
        </div>

        <HowItWorks />
        <BottomCTA />
      </div>
  );
};

export default Index;
