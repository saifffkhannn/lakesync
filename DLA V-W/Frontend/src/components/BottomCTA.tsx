import { Link } from "react-router-dom";

const BottomCTA = () => {
  return (
    <div className="py-16 bg-background relative">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="bg-card/80 backdrop-blur-xl rounded-3xl p-10 md:p-12 border border-border shadow-sm flex flex-col md:flex-row items-center justify-between gap-8">
          <div className="text-center md:text-left">
            <h2 className="text-2xl md:text-3xl font-bold text-foreground mb-3">
              Ready to Migrate Smarter?
            </h2>
            <p className="text-muted-foreground max-w-lg">
              Join thousands of teams who trust Synthlake AI for their data migration needs.
            </p>
          </div>
          <div className="flex items-center gap-4 flex-shrink-0">
            <Link to="/signup" className="btn-get-started">Get Started</Link>
            <Link to="/login" className="text-foreground bg-surface font-semibold px-8 py-3 rounded-full border border-border hover:bg-secondary transition-colors shadow-sm">
              Login
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BottomCTA;
