"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  Binary,
  Download,
  Home,
  Scissors,
  Settings,
} from "lucide-react";

import { cn } from "@/lib/cn";
import { useIsModelReady } from "@/hooks/useModelStatus";

const NAV_ITEMS = [
  { href: "/", label: "Load", icon: Home, requiresModel: false },
  { href: "/analyze", label: "Analyze", icon: Activity, requiresModel: true },
  { href: "/features", label: "Features", icon: Binary, requiresModel: true },
  { href: "/surgery", label: "Surgery", icon: Scissors, requiresModel: true },
  { href: "/export", label: "Export", icon: Download, requiresModel: true },
  { href: "/settings", label: "Settings", icon: Settings, requiresModel: false },
];

export default function Sidebar() {
  const pathname = usePathname();
  const modelReady = useIsModelReady();

  return (
    <aside className="w-56 shrink-0 border-r border-border bg-card flex flex-col">
      <div className="p-5 border-b border-border">
        <div className="font-mono text-lg font-semibold tracking-tight text-accent">
          NeuralScope
        </div>
        <div className="text-xs text-muted mt-1">v0.1.0 · phase 1</div>
      </div>
      <nav className="flex-1 p-3 space-y-1">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.href}
            item={item}
            active={pathname === item.href}
            disabled={item.requiresModel && !modelReady}
          />
        ))}
      </nav>
    </aside>
  );
}

function NavLink({ item, active, disabled }) {
  const Icon = item.icon;
  const classes = cn(
    "flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors",
    active && "bg-panel text-accent",
    !active && !disabled && "text-text hover:bg-panel",
    disabled && "text-muted pointer-events-none opacity-50",
  );

  if (disabled) {
    return (
      <div className={classes} aria-disabled>
        <Icon size={16} />
        <span>{item.label}</span>
      </div>
    );
  }

  return (
    <Link href={item.href} className={classes}>
      <Icon size={16} />
      <span>{item.label}</span>
    </Link>
  );
}
