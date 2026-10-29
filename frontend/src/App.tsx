import type { ReactNode } from "react";
import { Routes, Route } from "react-router-dom";
import { Navbar } from "./components/Navbar";
import { ToastProvider } from "./components/ToastProvider";
import { AuthProvider } from "./auth/AuthContext";
import { BrowsePage } from "./pages/BrowsePage";
import { AnimeDetailPage } from "./pages/AnimeDetailPage";
import { LoginPage, RegisterPage, SettingsPage } from "./pages/AuthPages";

function AniListFooter() {
  return (
    <footer className="app-footer">
      <p>Anime data provided by <a href="https://anilist.co" rel="noreferrer">AniList</a>.</p>
    </footer>
  );
}

function PageShell({ children }: { children: ReactNode }) {
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <Navbar />
      <main className="app-main" id="main-content">
        {children}
      </main>
      <AniListFooter />
    </div>
  );
}

export function App() {
  return (
    <ToastProvider>
      <AuthProvider>
        <PageShell>
          <Routes>
            <Route path="/" element={<BrowsePage />} />
            <Route path="/browse" element={<BrowsePage />} />
            <Route path="/anime/:id" element={<AnimeDetailPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="*" element={<p className="browse-page">Page not found</p>} />
          </Routes>
        </PageShell>
      </AuthProvider>
    </ToastProvider>
  );
}

export default App;
