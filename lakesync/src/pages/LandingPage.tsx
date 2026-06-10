import Architecture from '../components/Architecture';
import CTA from '../components/CTA';
import Features from '../components/Features';
import Footer from '../components/Footer';
import Hero from '../components/Hero';
import Navbar from '../components/Navbar';

export default function LandingPage({ onEnter }: { onEnter: () => void }) {
  return (
    <div className="min-h-screen bg-transparent">
      <Navbar onEnter={onEnter} />
      <main>
        <Hero onEnter={onEnter} />
        <Features />
        <Architecture />
        <CTA onEnter={onEnter} />
      </main>
      <Footer />
    </div>
  );
}
