
import React from "react";

/**
 * Shared application layout.
 *
 * Props:
 * - brand: Application name.
 * - links: Array of { label, href } navigation links.
 * - children: Page content.
 * - footer: Optional footer content.
 */
export default function SharedLayout({
  brand = "Event Management",
  links = [],
  children,
  footer = "Event Management System",
}) {
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>

      <header className="site-header">
        <a className="brand" href="/" aria-label={`${brand} home`}>
          {brand}
        </a>

        <nav aria-label="Main navigation">
          <ul className="shared-nav-list">
            {links.map((link) => (
              <li key={`${link.href}-${link.label}`}>
                <a href={link.href}>{link.label}</a>
              </li>
            ))}
          </ul>
        </nav>
      </header>

      <main id="main-content" className="page">
        {children}
      </main>

      <footer className="site-footer">
        <p>{footer}</p>
      </footer>
    </div>
  );
}
