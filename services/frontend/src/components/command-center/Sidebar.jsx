import React, { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import useLayoutStore from '../../stores/layoutStore'
import { PlatformLogo } from '../common/BrandLogos'

const navSections = [
  {
    label: 'WEATHER INTELLIGENCE',
    items: [
      {
        name: 'Command Center',
        href: '/',
        icon: (
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="3" width="7" height="7" rx="1" />
            <rect x="14" y="3" width="7" height="7" rx="1" />
            <rect x="14" y="14" width="7" height="7" rx="1" />
            <rect x="3" y="14" width="7" height="7" rx="1" />
          </svg>
        ),
      },
      {
        name: 'Live Events',
        href: '/events',
        icon: (
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
          </svg>
        ),
      },
      {
        name: 'Geospatial Intelligence',
        href: '/geospatial',
        icon: (
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6" />
            <line x1="8" y1="2" x2="8" y2="18" />
            <line x1="16" y1="6" x2="16" y2="22" />
          </svg>
        ),
      },
    ],
  },
  {
    label: 'ANALYTICS',
    items: [
      {
        name: 'Event Trends',
        href: '/analytics/events',
        icon: (
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
            <polyline points="17 6 23 6 23 12" />
          </svg>
        ),
      },
      {
        name: 'Geographic Analysis',
        href: '/analytics/geographic',
        icon: (
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="2" y1="12" x2="22" y2="12" />
            <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
          </svg>
        ),
      },
      {
        name: 'Source Intelligence',
        href: '/analytics/sources',
        icon: (
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M4 11a9 9 0 0 1 9 9" />
            <path d="M4 4a16 16 0 0 1 16 16" />
            <circle cx="5" cy="19" r="1" />
          </svg>
        ),
      },
    ],
  },
  {
    label: 'INTELLIGENCE',
    items: [
      {
        name: 'Emerging Events',
        href: '/emerging',
        icon: (
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="9" />
            <path d="M12 3v9l5 3" />
          </svg>
        ),
      },
    ],
  },
  {
    label: 'ADMIN',
    items: [
      {
        name: 'Verification Center',
        href: '/verification',
        icon: (
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
            <polyline points="22 4 12 14.01 9 11.01" />
          </svg>
        ),
      },
      {
        name: 'Report Review',
        href: '/report-review',
        icon: (
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="16" y1="13" x2="8" y2="13" />
            <line x1="16" y1="17" x2="8" y2="17" />
          </svg>
        ),
      },
      {
        name: 'System Monitoring',
        href: '/system-monitoring',
        icon: (
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="2" y="2" width="20" height="8" rx="2" ry="2" />
            <rect x="2" y="14" width="20" height="8" rx="2" ry="2" />
            <line x1="6" y1="6" x2="6.01" y2="6" />
            <line x1="6" y1="18" x2="6.01" y2="18" />
          </svg>
        ),
      },
    ],
  },
]

export default function Sidebar() {
  const location = useLocation()

  const {
    sidebarCollapsed,
    toggleSidebar,
    mobileDrawerOpen,
    setMobileDrawerOpen,
  } = useLayoutStore()

  const [hoveredNav, setHoveredNav] = useState(null)

  const isActive = (href) => {
    if (href === '/') return location.pathname === '/'
    return location.pathname.startsWith(href)
  }

  const sidebarContent = (
    <div className="flex flex-col h-full bg-white text-slate-800 select-none">
      {/* Brand Header */}
      <div className="h-[64px] px-3.5 border-b border-slate-200 flex items-center justify-between flex-shrink-0 bg-white">
        <PlatformLogo collapsed={sidebarCollapsed} size={sidebarCollapsed ? 'sm' : 'md'} />

        {/* Minimize / Expand Toggle on Desktop */}
        <button
          type="button"
          onClick={toggleSidebar}
          title={sidebarCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
          className="hidden lg:flex w-6 h-6 rounded-md hover:bg-slate-100 text-slate-400 hover:text-slate-700 items-center justify-center transition-colors flex-shrink-0"
        >
          <svg
            className={`w-3.5 h-3.5 transition-transform duration-200 ${
              sidebarCollapsed ? 'rotate-180' : ''
            }`}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
          >
            <polyline points="15 18 9 12 15 6" />
          </svg>
        </button>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-4 scrollbar-thin">
        {navSections.map((section) => (
          <div key={section.label}>
            {!sidebarCollapsed && (
              <div className="px-2.5 mb-1.5 text-[9.5px] font-bold tracking-wider text-slate-400 uppercase">
                {section.label}
              </div>
            )}

            <div className="space-y-0.5">
              {section.items.map((item) => {
                const active = isActive(item.href)

                return (
                  <div
                    key={item.name}
                    className="relative"
                    onMouseEnter={() => setHoveredNav(item.name)}
                    onMouseLeave={() => setHoveredNav(null)}
                  >
                    <Link
                      to={item.href}
                      onClick={() => setMobileDrawerOpen(false)}
                      className={`flex items-center gap-2.5 rounded-lg text-xs font-semibold transition-all duration-150 ${
                        sidebarCollapsed
                          ? 'justify-center p-2.5'
                          : 'px-2.5 py-2'
                      } ${
                        active
                          ? 'bg-brand-blue-50 text-brand-blue-700 border border-brand-blue-200/80 shadow-xs'
                          : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100 border border-transparent'
                      }`}
                    >
                      <span
                        className={`flex-shrink-0 transition-colors ${
                          active ? 'text-brand-blue-600' : 'text-slate-400'
                        }`}
                      >
                        {item.icon}
                      </span>

                      {!sidebarCollapsed && (
                        <span className="truncate">{item.name}</span>
                      )}

                      {!sidebarCollapsed && active && (
                        <span className="w-1.5 h-1.5 rounded-full bg-brand-blue-600 ml-auto flex-shrink-0" />
                      )}
                    </Link>

                    {/* Floating Tooltip in Collapsed Mode */}
                    {sidebarCollapsed && hoveredNav === item.name && (
                      <div className="absolute left-full ml-2 top-1/2 -translate-y-1/2 z-50 px-2.5 py-1 bg-slate-900 text-white text-[11px] font-semibold rounded-md shadow-lg whitespace-nowrap pointer-events-none animate-in fade-in-0 duration-100">
                        {item.name}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        ))}
      </nav>
    </div>
  )

  return (
    <>
      {/* Desktop Sidebar */}
      <aside
        className={`hidden lg:flex flex-col h-full border-r border-slate-200 flex-shrink-0 transition-all duration-300 ease-in-out ${
          sidebarCollapsed ? 'w-[72px]' : 'w-[260px]'
        }`}
      >
        {sidebarContent}
      </aside>

      {/* Mobile Drawer Backdrop & Slide-over */}
      {mobileDrawerOpen && (
        <div className="lg:hidden fixed inset-0 z-50 flex">
          {/* Backdrop */}
          <div
            onClick={() => setMobileDrawerOpen(false)}
            className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs transition-opacity animate-in fade-in-0 duration-200"
          />

          {/* Drawer Window */}
          <aside className="relative w-[280px] max-w-[80vw] h-full shadow-2xl z-10 animate-in slide-in-from-left duration-200">
            {sidebarContent}
          </aside>
        </div>
      )}
    </>
  )
}
