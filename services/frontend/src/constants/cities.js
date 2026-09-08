/**
 * SIH26069 — Cities Configuration
 * Active MVP Cities (Strict Data Scope):
 *  1. Mumbai (Coastal Urban Agglomeration)
 *  2. Nagpur (Vidarbha Inland Plain)
 *  3. Nashik (Western Ghats Plateau)
 *
 * All other Indian cities are marked as 'updated_soon'.
 */

export const ACTIVE_CITIES = [
  {
    name: 'Mumbai',
    aliases: ['mumbai', 'bombay'],
    state: 'Maharashtra',
    region: 'Konkan Coast',
    lat: 19.0760,
    lon: 72.8777,
    status: 'live',
    color: '#0284C7', // Sky / Deep Azure
    photo: '/city_mumbai.jpg',
    tagline: 'Coastal Metropolis',
    description: 'High-density urban precipitation, tidal surge & flash flood telemetry active.',
    weatherTypes: ['Monsoon Deluge', 'High Tide Surge', 'Urban Waterlogging'],
    sensors: '24 AWS Stations · 2 Radar Rings',
  },
  {
    name: 'Nagpur',
    aliases: ['nagpur'],
    state: 'Maharashtra',
    region: 'Vidarbha',
    lat: 21.1458,
    lon: 79.0882,
    status: 'live',
    color: '#EA580C', // Saffron / Orange
    photo: '/city_nagpur.jpg',
    tagline: 'Inland Central Hub',
    description: 'Extreme heatwave, high thermal stress & Nag river catchment telemetry active.',
    weatherTypes: ['Extreme Heatwave', 'Thermal Anomaly', 'Dust Thunderstorm'],
    sensors: '18 AWS Stations · 1 Doppler Radar',
  },
  {
    name: 'Nashik',
    aliases: ['nasik', 'nashik'],
    state: 'Maharashtra',
    region: 'Northern Western Ghats',
    lat: 19.9975,
    lon: 73.7898,
    status: 'live',
    color: '#059669', // Emerald Green
    photo: '/city_nashik.jpg',
    tagline: 'Ghats & Agro Basin',
    description: 'Thunderstorm, hailstorm & Godavari basin hydrology telemetry active.',
    weatherTypes: ['Ghats Rain', 'Hailstorm Alert', 'Godavari Discharge'],
    sensors: '14 AWS Stations · Micro-Barometer Grid',
  },
]

export const UPCOMING_CITIES = [
  { name: 'Pune', state: 'Maharashtra', region: 'Desh', lat: 18.5204, lon: 73.8567, status: 'updated_soon' },
  { name: 'Delhi NCR', state: 'National Capital', region: 'Northern Plains', lat: 28.6139, lon: 77.2090, status: 'updated_soon' },
  { name: 'Bengaluru', state: 'Karnataka', region: 'Deccan Plateau', lat: 12.9716, lon: 77.5946, status: 'updated_soon' },
  { name: 'Chennai', state: 'Tamil Nadu', region: 'Coromandel Coast', lat: 13.0827, lon: 80.2707, status: 'updated_soon' },
  { name: 'Kolkata', state: 'West Bengal', region: 'Ganges Delta', lat: 22.5726, lon: 88.3639, status: 'updated_soon' },
  { name: 'Hyderabad', state: 'Telangana', region: 'Telangana Plateau', lat: 17.3850, lon: 78.4867, status: 'updated_soon' },
  { name: 'Ahmedabad', state: 'Gujarat', region: 'Sabarmati Basin', lat: 23.0225, lon: 72.5714, status: 'updated_soon' },
  { name: 'Jaipur', state: 'Rajasthan', region: 'Aravalli Range', lat: 26.9124, lon: 75.7873, status: 'updated_soon' },
  { name: 'Lucknow', state: 'Uttar Pradesh', region: 'Awadh Plains', lat: 26.8467, lon: 80.9462, status: 'updated_soon' },
  { name: 'Chandigarh', state: 'Punjab/Haryana', region: 'Shivalik Foothills', lat: 30.7333, lon: 76.7794, status: 'updated_soon' },
  { name: 'Bhopal', state: 'Madhya Pradesh', region: 'Malwa Plateau', lat: 23.2599, lon: 77.4126, status: 'updated_soon' },
  { name: 'Patna', state: 'Bihar', region: 'Middle Ganges', lat: 25.5941, lon: 85.1376, status: 'updated_soon' },
  { name: 'Kochi', state: 'Kerala', region: 'Malabar Coast', lat: 9.9312, lon: 76.2673, status: 'updated_soon' },
  { name: 'Guwahati', state: 'Assam', region: 'Brahmaputra Valley', lat: 26.1445, lon: 91.7362, status: 'updated_soon' },
  { name: 'Bhubaneswar', state: 'Odisha', region: 'Eastern Coastal', lat: 20.2961, lon: 85.8245, status: 'updated_soon' },
]

export const ALL_CITY_OPTIONS = [
  { value: '', label: 'All Active Cities (3 Cities)', group: 'all' },
  ...ACTIVE_CITIES.map((c) => ({
    value: c.name,
    label: `${c.name}, ${c.state}`,
    city: c.name,
    state: c.state,
    status: 'live',
    color: c.color,
    photo: c.photo,
    group: 'active',
  })),
  ...UPCOMING_CITIES.map((c) => ({
    value: c.name,
    label: `${c.name}, ${c.state}`,
    city: c.name,
    state: c.state,
    status: 'updated_soon',
    group: 'upcoming',
    disabled: true,
  })),
]

export function isUpcomingCity(cityName) {
  if (!cityName) return false
  const activeNames = ['mumbai', 'nagpur', 'nasik', 'nashik']
  return !activeNames.includes(cityName.trim().toLowerCase())
}

export function getCityMetadata(cityName) {
  if (!cityName) return null
  const clean = cityName.trim().toLowerCase()
  return (
    ACTIVE_CITIES.find(
      (c) => c.name.toLowerCase() === clean || c.aliases.includes(clean)
    ) || null
  )
}

export function normalizeCityName(cityName) {
  if (!cityName) return ''
  const clean = cityName.trim().toLowerCase()
  if (clean === 'nashik' || clean === 'nasik') return 'Nashik'
  if (clean === 'mumbai') return 'Mumbai'
  if (clean === 'nagpur') return 'Nagpur'
  return cityName
}
