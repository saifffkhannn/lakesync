import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

const Signup = () => {
    const navigate = useNavigate();

    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");

    const handleSignup = (e: React.FormEvent) => {
        e.preventDefault();

        if (!email || !password || !confirmPassword) return;

        if (password !== confirmPassword) {
            alert("Passwords do not match");
            return;
        }

        // TEMP SIGNUP (no backend yet)
        navigate("/dashboard");
    };

    return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">

            <div className="w-full max-w-md bg-white p-8 rounded-2xl shadow-lg border border-gray-100">

                {/* Logo */}
                <div className="flex justify-center mb-6">
                    <img src="/logo.png" alt="logo" className="h-10" />
                </div>

                {/* Title */}
                <h2 className="text-2xl font-bold text-center text-gray-900">
                    Create Account
                </h2>

                <p className="text-center text-gray-500 mt-2 mb-6">
                    Start your data migration journey
                </p>

                {/* FORM */}
                <form onSubmit={handleSignup} className="space-y-4">

                    {/* Email */}
                    <div>
                        <label className="text-sm font-medium text-gray-700">
                            Email
                        </label>
                        <input
                            type="email"
                            placeholder="you@example.com"
                            className="w-full mt-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                        />
                    </div>

                    {/* Password */}
                    <div>
                        <label className="text-sm font-medium text-gray-700">
                            Password
                        </label>
                        <input
                            type="password"
                            placeholder="••••••••"
                            className="w-full mt-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                        />
                    </div>

                    {/* Confirm Password */}
                    <div>
                        <label className="text-sm font-medium text-gray-700">
                            Confirm Password
                        </label>
                        <input
                            type="password"
                            placeholder="••••••••"
                            className="w-full mt-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                            value={confirmPassword}
                            onChange={(e) => setConfirmPassword(e.target.value)}
                        />
                    </div>

                    {/* Button */}
                    <button
                        type="submit"
                        className="w-full bg-blue-600 hover:bg-blue-700 text-white py-2.5 rounded-lg font-semibold transition"
                    >
                        Create Account
                    </button>

                </form>

                {/* Footer */}
                <p className="text-sm text-center text-gray-500 mt-6">
                    Already have an account?{" "}
                    <Link to="/login" className="text-blue-600 font-medium">
                        Login
                    </Link>
                </p>

            </div>
        </div>
    );
};

export default Signup;