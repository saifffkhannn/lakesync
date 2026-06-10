import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { Mail, Lock, ArrowRight, ArrowLeft } from "lucide-react";

const Login = () => {
  const navigate = useNavigate();
  const { login } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();

    if (email && password) {
      setIsLoading(true);

      // Simulate API delay
      await new Promise((r) => setTimeout(r, 600));

      // Extract name from email (mock — replace with real API later)
      const namePart = email.split("@")[0];
      const name = namePart
        .replace(/[._-]/g, " ")
        .replace(/\b\w/g, (c) => c.toUpperCase());

      login({ name, email });
      navigate("/dashboard");
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-blue-50/30 to-gray-50 dark:from-gray-950 dark:via-gray-900 dark:to-gray-950 
      flex items-center justify-center px-4 transition-colors duration-300">
      
      <div className="w-full max-w-md">
        {/* Card */}
        <div className="bg-white dark:bg-gray-900 p-8 rounded-2xl shadow-xl shadow-gray-200/50 dark:shadow-gray-900/50 
          border border-gray-100 dark:border-gray-800">
          
          {/* Logo */}
          <div className="flex justify-center mb-8">
            <img src="/logo.png" alt="Synthlake AI" className="h-10 w-auto object-contain" />
          </div>

          {/* Title */}
          <h2 className="text-2xl font-bold text-center text-gray-900 dark:text-white">
            Welcome Back
          </h2>
          <p className="text-center text-gray-500 dark:text-gray-400 mt-2 mb-8">
            Login to your Synthlake account
          </p>

          {/* FORM */}
          <form onSubmit={handleLogin} className="space-y-5">
            {/* Email */}
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5 block">
                Email
              </label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-300 dark:text-gray-600" />
                <input
                  id="login-email"
                  type="email"
                  placeholder="you@example.com"
                  className="w-full pl-10 pr-4 py-2.5 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 
                    rounded-xl text-sm text-gray-800 dark:text-gray-200 placeholder-gray-400 dark:placeholder-gray-500
                    focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 dark:focus:border-blue-600 
                    transition-all duration-200"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
            </div>

            {/* Password */}
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5 block">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-300 dark:text-gray-600" />
                <input
                  id="login-password"
                  type="password"
                  placeholder="••••••••"
                  className="w-full pl-10 pr-4 py-2.5 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 
                    rounded-xl text-sm text-gray-800 dark:text-gray-200 placeholder-gray-400 dark:placeholder-gray-500
                    focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 dark:focus:border-blue-600 
                    transition-all duration-200"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>
            </div>

            {/* Button */}
            <button
              id="login-submit"
              type="submit"
              disabled={isLoading}
              className="w-full bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-700 hover:to-blue-600 
                text-white py-3 rounded-xl font-semibold text-sm
                shadow-lg shadow-blue-500/20 hover:shadow-blue-500/30
                disabled:opacity-60 disabled:cursor-not-allowed
                flex items-center justify-center gap-2 transition-all duration-200"
            >
              {isLoading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  Login <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          {/* Back Button */}
          <div className="mt-6 pt-6 border-t border-gray-100 dark:border-gray-800">
            <button
              onClick={() => navigate("/")}
              className="w-full flex items-center justify-center gap-2 text-sm font-medium text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
            >
              <ArrowLeft className="w-4 h-4" /> Back to Home
            </button>
          </div>

          {/* Footer */}
          <p className="text-sm text-center text-gray-500 dark:text-gray-400 mt-8">
            Don't have an account?{" "}
            <Link
              to="/signup"
              className="text-blue-600 dark:text-blue-400 font-semibold hover:text-blue-700 dark:hover:text-blue-300 transition-colors"
            >
              Sign up
            </Link>
          </p>
        </div>

        {/* Bottom text */}
        <p className="text-center text-xs text-gray-400 dark:text-gray-600 mt-6">
          © 2026 Synthlake AI. All rights reserved.
        </p>
      </div>
    </div>
  );
};

export default Login;
