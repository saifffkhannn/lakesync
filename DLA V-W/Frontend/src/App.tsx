import { Routes, Route } from "react-router-dom"
import { AuthProvider } from "./contexts/AuthContext"
import { ThemeProvider } from "./contexts/ThemeContext"
import ToastContainer from "./components/ui/Toast"
 
// NEW PAGES
import LandingPage from "./pages/LandingPage"
import Login from "./pages/Login"
import Signup from "./pages/Signup"
import Dashboard from "./pages/Dashboard"
 
// EXISTING PAGES (DON'T TOUCH)
import Connection from "./pages/connection"
import SourceMapper from "./pages/SourceMapper"
import MigrationProgress from "./pages/MigrationProgress"
 
function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <ToastContainer />
        <Routes>
 
          {/* NEW FLOW */}
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="/dashboard" element={<Dashboard />} />
 
          {/* EXISTING FLOW (CONFIG PIPELINE) */}
          <Route path="/config" element={<Connection />} />
          <Route path="/mapper" element={<SourceMapper />} />
          <Route path="/progress" element={<MigrationProgress />} />
 
        </Routes>
      </AuthProvider>
    </ThemeProvider>
  )
}
 
export default App
 