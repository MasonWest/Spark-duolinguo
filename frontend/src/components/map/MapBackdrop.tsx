/**
 * 氛围层。
 *
 * 硬约束：本组件只提供氛围，不承担任何信息表达。
 * 它不接收任何 props，不知道课程、Level、状态、进度的存在 ——
 * 把它整个删掉，地图的结构与状态依然完整可读。
 *
 * 用 sticky + 负 margin 实现"远景几乎不动"的轻量视差，纯 CSS，无 JS 监听 scroll。
 */
export default function MapBackdrop() {
  return (
    <div className="map-backdrop" aria-hidden="true">
      <svg
        className="bd-clouds"
        viewBox="0 0 720 130"
        preserveAspectRatio="none"
        height="130"
      >
        <g fill="#ffffff" opacity="0.55">
          <ellipse cx="120" cy="46" rx="62" ry="19" />
          <ellipse cx="164" cy="38" rx="40" ry="15" />
          <ellipse cx="470" cy="72" rx="74" ry="21" />
          <ellipse cx="524" cy="64" rx="44" ry="15" />
          <ellipse cx="640" cy="34" rx="52" ry="16" />
        </g>
      </svg>

      <svg
        className="bd-hills"
        viewBox="0 0 720 170"
        preserveAspectRatio="none"
        height="170"
      >
        <path d="M0 122 L118 62 L214 108 L318 48 L438 118 L556 74 L668 120 L720 96 L720 170 L0 170 Z" fill="#dfe9f4" opacity="0.75" />
        <path d="M0 148 L96 108 L206 146 L332 104 L452 150 L574 116 L690 148 L720 136 L720 170 L0 170 Z" fill="#cfdcea" opacity="0.85" />
      </svg>
    </div>
  );
}
