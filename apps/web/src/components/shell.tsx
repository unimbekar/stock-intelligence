"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useLayoutEffect, useState } from "react";

import { api } from "@/lib/client";
import { primaryNav, secondaryNav } from "@/lib/nav";

const themeBoot = `try{var t=localStorage.getItem("meridian-theme");document.documentElement.classList.toggle("dark",t!=="light")}catch(e){}`;

export function ThemeBoot() {
  return <script dangerouslySetInnerHTML={{ __html: themeBoot }} />;
}

export function ThemeSync() {
  useLayoutEffect(() => {
    const light = localStorage.getItem("meridian-theme") === "light";
    document.documentElement.classList.toggle("dark", !light);
  }, []);
  return null;
}

export function Shell({
  children,
  dataModeLabel,
}: {
  children: React.ReactNode;
  dataModeLabel: string;
}) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [badge, setBadge] = useState(dataModeLabel);
  const [signedIn, setSignedIn] = useState(false);

  useEffect(() => {
    api<{ dataModeLabel: string }>("/api/v1/meta").then((result) => {
      if (result.body?.dataModeLabel) setBadge(result.body.dataModeLabel);
    });
    api<{ email: string }>("/api/v1/auth/me").then((result) => setSignedIn(result.ok));
  }, [pathname]);

  function toggleTheme() {
    const next = !document.documentElement.classList.contains("dark");
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("meridian-theme", next ? "dark" : "light");
  }

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[240px_1fr]">
      <aside
        className={`${open ? "block" : "hidden"} border-b border-line bg-elevated lg:block lg:border-b-0 lg:border-r`}
      >
        <div className="flex items-center justify-between px-4 py-4">
          <Link href="/" className="block" onClick={() => setOpen(false)}>
            <span className="text-[11px] tracking-[0.22em] text-muted uppercase">Meridian</span>
            <span className="mt-1 block text-sm text-ink">Equity desk</span>
          </Link>
        </div>
        <nav aria-label="Primary" className="px-2 pb-4">
          <ul className="space-y-0.5">
            {primaryNav.map((item) => (
              <li key={item.href}>
                <NavLink href={item.href} pathname={pathname} onNavigate={() => setOpen(false)}>
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>
          <p className="mt-6 px-3 text-[11px] tracking-[0.16em] text-muted uppercase">Workspace</p>
          <ul className="mt-1 space-y-0.5">
            {secondaryNav.map((item) => (
              <li key={item.href}>
                <NavLink href={item.href} pathname={pathname} onNavigate={() => setOpen(false)}>
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
      </aside>
      <div className="min-w-0">
        <header className="flex items-center justify-between gap-3 border-b border-line px-4 py-3">
          <button
            type="button"
            className="border border-line px-2 py-1 text-sm lg:hidden"
            aria-expanded={open}
            onClick={() => setOpen((value) => !value)}
          >
            Menu
          </button>
          <p className="text-xs tracking-[0.14em] text-warning uppercase">{badge}</p>
          <div className="flex items-center gap-2">
            {signedIn ? (
              <button
                type="button"
                className="border border-line px-2 py-1 text-sm"
                onClick={() => {
                  api("/api/v1/auth/logout", { method: "POST" }).then(() => setSignedIn(false));
                }}
              >
                Sign out
              </button>
            ) : (
              <Link href="/login" className="border border-line px-2 py-1 text-sm">
                Sign in
              </Link>
            )}
            <button type="button" className="border border-line px-2 py-1 text-sm" onClick={toggleTheme}>
              Switch theme
            </button>
          </div>
        </header>
        <main className="px-4 py-6 sm:px-6">{children}</main>
      </div>
    </div>
  );
}

function NavLink({
  href,
  pathname,
  children,
  onNavigate,
}: {
  href: string;
  pathname: string;
  children: React.ReactNode;
  onNavigate: () => void;
}) {
  const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      onClick={onNavigate}
      className={`block px-3 py-1.5 text-sm ${active ? "bg-muted-surface text-ink" : "text-muted hover:text-ink"}`}
    >
      {children}
    </Link>
  );
}
