import React from "react";
import { Routes, Route } from "react-router-dom";
import { Navbar } from "./components/Navbar";
import { HomePage } from "./pages/HomePage";

/**
 * Main Application Component:
 * Wraps pages in the common dark shell and mounts the React Router routes.
 */
export const App: React.FC = () => {
  return (
    <div className="flex min-h-screen flex-col bg-surface-base text-content-primary">
      <Navbar />
      <main className="flex-1">
        <Routes>
          <Route path="/" element={<HomePage />} />
        </Routes>
      </main>
      <footer className="border-t border-surface-border py-8 text-center text-xs text-content-muted">
        <p>
          AniMatch &copy; {new Date().getFullYear()} &mdash; AI Anime
          Recommendation Engine
        </p>
      </footer>
    </div>
  );
};

export default App;
