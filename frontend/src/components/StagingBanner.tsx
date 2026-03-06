// Renders an unmissable amber banner when VITE_APP_ENV is not 'production'.
// undefined (local dev, no build arg) also shows the banner — safe default.
export default function StagingBanner() {
  if (import.meta.env.VITE_APP_ENV === 'production') return null

  return (
    <div className="w-full bg-amber-400 text-gray-900 text-center text-sm font-bold py-2 px-4 sticky top-0 z-50">
      STAGING -- Not Production
    </div>
  )
}
