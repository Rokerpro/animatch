import React from "react";
import { Link } from "react-router-dom";
import { Sparkles } from "lucide-react";

/**
 * Navbar Component:
 * Follows a minimal dark design with a glassmorphism backdrop blur,
 * high-contrast typography, and a single violet/indigo accent indicator.
 */
export const Navbar: React.FC = () => {
  return (
    <header className="sticky top-0 z-50 w-full border-b border-surface-border bg-surface-base/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Brand Logo */}
        <Link
          to="/"
          className="group flex items-center gap-2.5 text-lg font-semibold tracking-tight text-content-primary transition duration-200 hover:text-white"
        >
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-surface-raised border border-surface-border group-hover:border-accent/40 transition">
            <Sparkles className="h-4 w-4 text-accent transition duration-200 group-hover:scale-110" />
          </div>
          <span>
            Ani<span className="text-accent">Match</span>
          </span>
        </Link>

        {/* Minimal Navigation Links */}
        <nav className="flex items-center gap-6">
          <Link
            to="/"
            className="text-sm font-medium text-content-secondary hover:text-content-primary transition duration-200"
          >
            Home
          </Link>
          <span className="text-xs uppercase tracking-widest px-2.5 py-1 rounded bg-surface-raised border border-surface-border text-content-muted">
            Phase 1 Scaffold
          </span>
        </nav>
      </div>
    </header>
  );
};
