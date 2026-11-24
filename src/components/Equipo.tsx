/** Guampa de palo santo con virolas de acero y bombilla con filtro, en SVG. */
export function Guampa({ className = '' }: { className?: string }) {
  return (
    <svg className={`guampa ${className}`} viewBox="0 0 220 320" aria-hidden="true" focusable="false">
      <defs>
        <linearGradient id="palo-santo" x1="0" x2="1">
          <stop offset="0" stopColor="#3f3a1c" />
          <stop offset=".25" stopColor="#7c7440" />
          <stop offset=".4" stopColor="#a39a5c" />
          <stop offset=".6" stopColor="#6d6533" />
          <stop offset="1" stopColor="#35301a" />
        </linearGradient>
        <linearGradient id="virola" x1="0" x2="1">
          <stop offset="0" stopColor="#7d868d" />
          <stop offset=".35" stopColor="#ffffff" />
          <stop offset=".6" stopColor="#b9c1c7" />
          <stop offset="1" stopColor="#6c757c" />
        </linearGradient>
      </defs>
      <ellipse cx="104" cy="304" rx="70" ry="9" fill="#000" opacity=".25" />
      {/* bombilla: entra en diagonal y asoma por arriba */}
      <path d="M150 10 L150 26 Q150 34 142 40 L112 230" fill="none" stroke="url(#virola)" strokeWidth="7" strokeLinecap="round" />
      <ellipse cx="111" cy="238" rx="13" ry="18" fill="url(#virola)" />
      {/* cuerpo de la guampa, un poco más ancho arriba */}
      <path d="M48 92 L160 92 L150 290 Q104 304 58 290 Z" fill="url(#palo-santo)" />
      {/* vetas de la madera */}
      <g stroke="#2c2814" strokeOpacity=".35" fill="none" strokeWidth="1.4">
        <path d="M74 110 C80 160, 70 210, 78 280" />
        <path d="M120 104 C114 160, 128 220, 120 286" />
        <path d="M140 112 C136 170, 146 220, 138 282" />
      </g>
      {/* yerba mojada asomando */}
      <ellipse cx="104" cy="92" rx="56" ry="10" fill="#4f7a2c" />
      <ellipse cx="104" cy="90" rx="50" ry="7" fill="#7aa847" />
      {/* virolas de acero */}
      <rect x="44" y="84" width="120" height="16" rx="5" fill="url(#virola)" />
      <rect x="54" y="276" width="100" height="14" rx="5" fill="url(#virola)" />
    </svg>
  )
}
