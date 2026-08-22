/** Line icons, drawn inline rather than pulled from a package.
 *
 *  They inherit `currentColor` and a single stroke weight, so one set stays legible on the
 *  navy hero, on the gold band, and in a greyscale print of the page. A dependency for
 *  twenty paths would also be a dependency to keep pinned across six laptops.
 */
export type IconName =
  | "rupee" | "chart" | "doc" | "check" | "ban" | "upload" | "scan" | "gauge"
  | "link" | "shield" | "clock" | "road" | "water" | "building" | "bolt"
  | "arrow" | "users" | "flag" | "search" | "layers"
  | "cpu" | "lock" | "list" | "cloud" | "trend" | "pie" | "play" | "docCheck"
  | "bell" | "settings" | "help" | "logout" | "grid" | "folder" | "filter"
  | "chevronDown" | "chevronRight" | "close" | "columns" | "expandLeft" | "expandRight"
  | "target" | "quote" | "sparkle" | "book" | "history" | "download" | "menu";

const PATHS: Record<IconName, React.ReactNode> = {
  rupee:    <><path d="M7 4h10M7 8h10M17 4c0 4-3.5 5-7 5l7 11" /></>,
  chart:    <><path d="M4 20V9M10 20V4M16 20v-7M22 20H2" /></>,
  doc:      <><path d="M6 2h8l4 4v16H6z" /><path d="M14 2v4h4" /><path d="M9 13h6M9 17h4" /></>,
  check:    <><circle cx="12" cy="12" r="9" /><path d="m8 12 3 3 5-6" /></>,
  ban:      <><circle cx="12" cy="12" r="9" /><path d="m6 6 12 12" /></>,
  upload:   <><path d="M12 16V4M8 8l4-4 4 4" /><path d="M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3" /></>,
  scan:     <><path d="M3 7V4h3M18 4h3v3M21 17v3h-3M6 20H3v-3" /><path d="M7 12h10" /></>,
  gauge:    <><path d="M4 18a8 8 0 1 1 16 0" /><path d="m12 18 4.5-6" /><circle cx="12" cy="18" r="1.3" /></>,
  link:     <><path d="M10 13a5 5 0 0 0 7 0l2-2a5 5 0 0 0-7-7l-1 1" /><path d="M14 11a5 5 0 0 0-7 0l-2 2a5 5 0 0 0 7 7l1-1" /></>,
  shield:   <><path d="M12 3l8 3v6c0 5-3.4 8.3-8 9.6C7.4 20.3 4 17 4 12V6z" /><path d="m9 12 2 2 4-4" /></>,
  clock:    <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3.5 2" /></>,
  road:     <><path d="M6 21 9 3M18 21 15 3" /><path d="M12 5v3M12 12v3M12 18v2" /></>,
  water:    <><path d="M12 3s6 6.6 6 10.5A6 6 0 0 1 6 13.5C6 9.6 12 3 12 3z" /></>,
  building: <><path d="M4 21V6l7-3 7 3v15" /><path d="M2 21h20" /><path d="M9 21v-5h5v5" /><path d="M8 9h2M14 9h2M8 13h2M14 13h2" /></>,
  bolt:     <><path d="M13 2 4 14h7l-1 8 9-12h-7z" /></>,
  arrow:    <><path d="M5 12h14M13 6l6 6-6 6" /></>,
  users:    <><circle cx="9" cy="8" r="3.2" /><path d="M3 20c0-3.3 2.7-5.4 6-5.4s6 2.1 6 5.4" /><path d="M16 5.2A3.2 3.2 0 0 1 16 11M18 20c0-2.4-.9-4.1-2.4-5.1" /></>,
  flag:     <><path d="M5 21V4M5 5h12l-2 4 2 4H5" /></>,
  search:   <><circle cx="11" cy="11" r="7" /><path d="m20 20-4-4" /></>,
  layers:   <><path d="m12 3 9 5-9 5-9-5z" /><path d="m3 13 9 5 9-5" /></>,
  cpu:      <><rect x="7" y="7" width="10" height="10" rx="1.5" /><rect x="3.5" y="3.5" width="17" height="17" rx="3" strokeWidth="1.3" /><path d="M12 3.5V1M12 23v-2.5M3.5 12H1M23 12h-2.5" /></>,
  lock:     <><rect x="4.5" y="10" width="15" height="11" rx="2" /><path d="M8 10V7a4 4 0 0 1 8 0v3" /><path d="M12 14.5v2.5" /></>,
  list:     <><path d="M9 6h11M9 12h11M9 18h11" /><path d="m3.5 5.5 1.2 1.2L7 4.5M3.5 11.5l1.2 1.2L7 10.5M3.5 17.5l1.2 1.2L7 16.5" strokeWidth="1.5" /></>,
  cloud:    <><path d="M7 18a4 4 0 0 1-.4-8 5.5 5.5 0 0 1 10.6 1.2A3.6 3.6 0 0 1 17 18" /><path d="M12 21v-8M9.5 15.5 12 13l2.5 2.5" /></>,
  trend:    <><path d="M3 20h18" /><path d="m4 15 5-5 3.5 3.5L20 6" /><path d="M20 11V6h-5" /></>,
  pie:      <><path d="M12 3a9 9 0 1 0 9 9h-9z" /><path d="M14.5 2.5A9 9 0 0 1 21.5 9.5h-7z" /></>,
  play:     <><circle cx="12" cy="12" r="9" /><path d="M10 8.5 16 12l-6 3.5z" /></>,
  docCheck: <><path d="M6 2h8l4 4v16H6z" /><path d="M14 2v4h4" /><path d="m9 14 2 2 4-4" /></>,
  bell:     <><path d="M18 9a6 6 0 1 0-12 0c0 5-2 6-2 6h16s-2-1-2-6" /><path d="M10.5 20a2 2 0 0 0 3 0" /></>,
  settings: <><circle cx="12" cy="12" r="3" /><path d="M12 2.5v2.2M12 19.3v2.2M4.2 7.2l1.9 1.1M17.9 15.7l1.9 1.1M4.2 16.8l1.9-1.1M17.9 8.3l1.9-1.1" /></>,
  help:     <><circle cx="12" cy="12" r="9" /><path d="M9.6 9.4a2.5 2.5 0 1 1 3.3 2.4c-.6.2-.9.8-.9 1.4v.4" /><path d="M12 17h.01" /></>,
  logout:   <><path d="M15 4h3a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1h-3" /><path d="M10 8l-4 4 4 4M6 12h9" /></>,
  grid:     <><rect x="3.5" y="3.5" width="7" height="7" rx="1.5" /><rect x="13.5" y="3.5" width="7" height="7" rx="1.5" /><rect x="3.5" y="13.5" width="7" height="7" rx="1.5" /><rect x="13.5" y="13.5" width="7" height="7" rx="1.5" /></>,
  folder:   <><path d="M3 7a1 1 0 0 1 1-1h5l2 2.5h9a1 1 0 0 1 1 1V18a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z" /></>,
  filter:   <><path d="M3.5 5.5h17l-6.5 7.5V20l-4-2.2v-5z" /></>,
  chevronDown:  <><path d="m6 9 6 6 6-6" /></>,
  chevronRight: <><path d="m9 6 6 6-6 6" /></>,
  close:    <><path d="M6 6l12 12M18 6 6 18" /></>,
  columns:  <><rect x="3" y="4.5" width="18" height="15" rx="2" /><path d="M12 4.5v15" /></>,
  expandLeft:  <><rect x="3" y="4.5" width="18" height="15" rx="2" /><path d="M15 4.5v15" /><path d="M9 9.5 6.5 12 9 14.5" /></>,
  expandRight: <><rect x="3" y="4.5" width="18" height="15" rx="2" /><path d="M9 4.5v15" /><path d="m15 9.5 2.5 2.5L15 14.5" /></>,
  target:   <><circle cx="12" cy="12" r="8.5" /><circle cx="12" cy="12" r="4.2" /><circle cx="12" cy="12" r="1" /></>,
  quote:    <><path d="M9 7c-3 1-4.5 3.4-4.5 6.4V17H10v-5.2H7.2C7.4 9.8 8.2 8.6 10 7.8zM20 7c-3 1-4.5 3.4-4.5 6.4V17H21v-5.2h-2.8c.2-2 1-3.2 2.8-4z" /></>,
  sparkle:  <><path d="m12 3 1.9 5.3L19 10l-5.1 1.7L12 17l-1.9-5.3L5 10l5.1-1.7z" /><path d="M18.5 16.5 19 18l1.5.5L19 19l-.5 1.5L18 19l-1.5-.5L18 18z" /></>,
  book:     <><path d="M4 5.5A1.5 1.5 0 0 1 5.5 4H11v16H5.5A1.5 1.5 0 0 1 4 18.5z" /><path d="M20 5.5A1.5 1.5 0 0 0 18.5 4H13v16h5.5a1.5 1.5 0 0 0 1.5-1.5z" /></>,
  history:  <><path d="M3.5 12a8.5 8.5 0 1 0 2.6-6.1" /><path d="M3.5 4.5V10h5.5" /><path d="M12 8v4.3l3 1.8" /></>,
  download: <><path d="M12 4v11M8 11l4 4 4-4" /><path d="M4 19h16" /></>,
  menu:     <><path d="M4 7h16M4 12h16M4 17h16" /></>,
};

export function Icon({ name, className = "" }: { name: IconName; className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7"
         strokeLinecap="round" strokeLinejoin="round" aria-hidden
         className={`shrink-0 ${className}`}>
      {PATHS[name]}
    </svg>
  );
}
