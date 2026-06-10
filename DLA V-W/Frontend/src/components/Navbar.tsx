import { Link } from "react-router-dom";
import { Moon, Sun, Menu, X } from "lucide-react";
import { useTheme } from "@/hooks/useTheme";
import { useState } from "react";
import { motion } from "framer-motion";
import logo from "@/assets/synthlake_light.png";

const navLinks = [
  { label: "Home", href: "home" },
  { label: "Features", href: "features" },
  { label: "How It Works", href: "how-it-works" },
  { label: "Use Cases", href: "use-cases" },
];

const Navbar = () => {
  const { theme, toggleTheme } = useTheme();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [active, setActive] = useState("Home");

  // ✅ Smooth scroll navigation
  const handleNavClick = (label: string, id: string) => {
    setActive(label);

    const section = document.getElementById(id);

    if (section) {
      const navbarHeight = 80; // adjust if needed

      const elementPosition =
        section.getBoundingClientRect().top + window.scrollY;

      const offsetPosition = elementPosition - navbarHeight;

      window.scrollTo({
        top: offsetPosition,
        behavior: "smooth",
      });
    }

    setMobileOpen(false);
  };

  return (
    <header className="sticky top-0 z-50 w-full backdrop-blur-xl bg-white/70 dark:bg-slate-950/70 border-b border-slate-200/60 dark:border-slate-800/60">
      <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">

          {/* LOGO + PRODUCT LOCKUP */}
          <Link to="/" className="flex items-center gap-3 group">
            <img
              src={logo}
              alt="Synthlake"
              className="h-12 w-auto transition-transform group-hover:scale-[1.02]"
            />

            {/* Thin vertical divider */}
            <span
              aria-hidden="true"
              className="h-6 w-px bg-gradient-to-b from-transparent via-slate-300 to-transparent dark:via-slate-600"
            />

            {/* Product name */}
            <div className="flex flex-col leading-none">
              <span className="text-base font-bold bg-gradient-to-r from-blue-600 to-cyan-500 bg-clip-text text-transparent">
                HyperLoad
              </span>
            </div>
          </Link>


          {/* NAV LINKS */}
          <div className="hidden md:flex items-center gap-6">
            {navLinks.map((link) => {
              const isActive = active === link.label;

              return (
                <button
                  key={link.label}
                  onClick={() => handleNavClick(link.label, link.href)}
                  className="relative text-sm font-medium"
                >
                  {/* ACTIVE UNDERLINE */}
                  {isActive && (
                    <motion.div
                      layoutId="nav-underline"
                      className="absolute left-0 -bottom-1 h-[2px] w-full bg-blue-600 dark:bg-blue-400"
                      transition={{ type: "spring", stiffness: 400, damping: 30 }}
                    />
                  )}

                  {/* TEXT */}
                  <motion.span
                    whileHover={{ scale: 1.08 }}
                    animate={{ scale: isActive ? 1.1 : 1 }}
                    transition={{ type: "spring", stiffness: 300 }}
                    className={`transition-colors ${isActive
                      ? "text-blue-600 dark:text-blue-400 font-semibold"
                      : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
                      }`}
                  >
                    {link.label}
                  </motion.span>
                </button>
              );
            })}
          </div>

          {/* RIGHT SIDE */}
          <div className="flex items-center gap-3">
            {/* Theme toggle */}
            <button
              onClick={toggleTheme}
              className="p-2 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 transition"
            >
              {theme === "light" ? (
                <Moon className="w-4 h-4" />
              ) : (
                <Sun className="w-4 h-4" />
              )}
            </button>

            {/* Login */}
            <Link
              to="/login"
              className="hidden sm:inline-flex px-4 py-2 text-sm font-medium border rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 transition"
            >
              Login
            </Link>

            {/* ✅ GET STARTED BUTTON */}
            <Link
              to="/signup"
              className="hidden sm:inline-flex btn-get-started !px-5 !py-2 text-sm"
            >
              Get Started
            </Link>

            {/* Mobile toggle */}
            <button
              onClick={() => setMobileOpen(!mobileOpen)}
              className="md:hidden p-2"
            >
              {mobileOpen ? <X /> : <Menu />}
            </button>
          </div>
        </div>

        {/* MOBILE */}
        {mobileOpen && (
          <div className="md:hidden pb-4 pt-2 space-y-1 animate-in fade-in slide-in-from-top-2 duration-200">
            {navLinks.map((link) => {
              const isActive = active === link.label;

              return (
                <button
                  key={link.label}
                  onClick={() => handleNavClick(link.label, link.href)}
                  className={`block w-full text-left px-4 py-2 rounded-lg text-sm ${isActive
                    ? "text-blue-600 bg-blue-50 dark:bg-blue-500/10"
                    : "hover:bg-slate-100 dark:hover:bg-slate-800"
                    }`}
                >
                  {link.label}
                </button>
              );
            })}

            <div className="flex gap-2 pt-3">
              <Link to="/login" className="flex-1 text-center border py-2 rounded-full">
                Login
              </Link>
              <Link to="/signup" className="flex-1 text-center btn-get-started">
                Get Started
              </Link>
            </div>
          </div>
        )}
      </nav>
    </header>
  );
};

export default Navbar;