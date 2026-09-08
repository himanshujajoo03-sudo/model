/**
 * Map styling theme for India state boundaries, surrounding landmass, and city nodes.
 * Designed specifically for a clean white page canvas (#FFFFFF).
 */

// Distinct, harmonious pastel-tinted land fills for Indian states
// Ensuring neighboring states never share the same fill color.
export const STATE_COLOR_MAP = {
  'Maharashtra': '#EEF2FF',      // Soft Indigo / Lavender
  'Gujarat': '#FFF7ED',          // Soft Saffron / Orange
  'Madhya Pradesh': '#F0FDFA',    // Soft Mint / Teal
  'Rajasthan': '#FEFCE8',        // Soft Golden Amber
  'Karnataka': '#ECFDF5',        // Soft Emerald
  'Goa': '#FDF2F8',              // Soft Fuchsia / Pink
  'Telangana': '#F0F9FF',        // Soft Sky Blue
  'Andhra Pradesh': '#FAF5FF',   // Soft Purple / Violet
  'Tamil Nadu': '#FFF1F2',       // Soft Rose
  'Kerala': '#DCFCE7',           // Soft Meadow Green
  'Chhattisgarh': '#FEF3C7',     // Soft Warm Gold
  'Odisha': '#EDE9FE',           // Soft Periwinkle
  'West Bengal': '#FEF9C3',      // Soft Sun Gold
  'Jharkhand': '#E0E7FF',        // Soft Blue-Indigo
  'Bihar': '#FCE7F3',            // Soft Orchid
  'Uttar Pradesh': '#F5F3FF',    // Soft Iris Violet
  'Uttarakhand': '#CFFAFE',      // Soft Glacial Cyan
  'Himachal Pradesh': '#E0F2FE', // Soft Alpine Azure
  'Punjab': '#FDF4FF',           // Soft Lilac
  'Haryana': '#FEF3C7',          // Soft Wheat Amber
  'Delhi': '#FFE4E6',            // Soft Coral
  'Jammu and Kashmir': '#E2E8F0',// Soft Snow Slate
  'Ladakh': '#EDE8E3',           // Soft High-Altitude Sand
  'Sikkim': '#D1FAE5',           // Soft Himalayan Mint
  'Assam': '#CCFBF1',            // Soft Brahmaputra Teal
  'Arunachal Pradesh': '#E0F2FE',// Soft Dawn Cyan
  'Meghalaya': '#EEF2FF',        // Soft Cloud Indigo
  'Nagaland': '#FEF3C7',         // Soft Amber
  'Manipur': '#FCE7F3',          // Soft Pink
  'Mizoram': '#ECFDF5',          // Soft Green
  'Tripura': '#F5F3FF',          // Soft Violet
}

// Fallback palette for any UT or unmapped region
const FALLBACK_PALETTE = [
  '#EEF2FF', '#FFF7ED', '#F0FDFA', '#FEFCE8',
  '#ECFDF5', '#FAF5FF', '#F0F9FF', '#FFF1F2',
]

export function getStateColor(stateName) {
  if (!stateName) return '#F8FAFC'
  if (STATE_COLOR_MAP[stateName]) return STATE_COLOR_MAP[stateName]
  // Deterministic hash fallback
  let hash = 0
  for (let i = 0; i < stateName.length; i++) {
    hash = stateName.charCodeAt(i) + ((hash << 5) - hash)
  }
  const idx = Math.abs(hash) % FALLBACK_PALETTE.length
  return FALLBACK_PALETTE[idx]
}

// Surrounding countries (Pakistan, China, Nepal, Bhutan, Bangladesh, Myanmar, Sri Lanka)
export const SURROUNDING_LAND_STYLE = {
  fillColor: '#F1F5F9',
  fillOpacity: 0.85,
  color: '#CBD5E1',
  weight: 1,
  dashArray: '2, 2',
}

// Default state boundary vector style
export const DEFAULT_STATE_STYLE = {
  fillOpacity: 0.8,
  color: '#64748B',      // Slate-500 distinct state border
  weight: 1.2,
  opacity: 0.9,
}

// Hover state boundary vector style
export const HOVER_STATE_STYLE = {
  fillOpacity: 0.95,
  color: '#1E3A8A',      // High-contrast Deep Blue
  weight: 2.2,
  opacity: 1,
}

// City Beacon Node Styles for the 3 active cities
export const CITY_BEACON_STYLES = {
  'Mumbai': {
    color: '#0284C7',
    label: 'Mumbai',
    tag: 'Coastal Metro',
    subtext: 'Konkan Coast',
  },
  'Nagpur': {
    color: '#EA580C',
    label: 'Nagpur',
    tag: 'Vidarbha Hub',
    subtext: 'Central Inland',
  },
  'Nasik': {
    color: '#059669',
    label: 'Nashik',
    tag: 'Ghats Basin',
    subtext: 'Western Ghats',
  },
  'Nashik': {
    color: '#059669',
    label: 'Nashik',
    tag: 'Ghats Basin',
    subtext: 'Western Ghats',
  },
}
