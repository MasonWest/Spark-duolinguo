import type { FC } from "react";

interface Props {
  percentage: number;
  size?: number;
  strokeWidth?: number;
  showLabel?: boolean;
  className?: string;
  "aria-label"?: string;
}

const ProgressRing: FC<Props> = ({
  percentage,
  size = 64,
  strokeWidth = 6,
  showLabel = false,
  className = "",
  "aria-label": ariaLabel,
}) => {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - Math.max(0, Math.min(100, percentage)) / 100);

  return (
    <svg
      className={`progress-ring ${className}`}
      width={size}
      height={size}
      role="img"
      aria-label={ariaLabel}
      style={{ "--size": `${size}px`, "--stroke": strokeWidth, "--dash": circumference, "--offset": offset } as React.CSSProperties}
    >
      <circle
        className="progress-ring__bg"
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
      />
      <circle
        className="progress-ring__fg"
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        strokeLinecap="round"
      />
      {showLabel && (
        <text
          x={size / 2}
          y={size / 2 + 4}
          textAnchor="middle"
          dominantBaseline="middle"
          fontSize={size * 0.22}
          fontWeight={700}
          fill="var(--sq-text)"
          fontFamily="system-ui, -apple-system, Segoe UI, sans-serif"
        >
          {Math.round(percentage)}%
        </text>
      )}
    </svg>
  );
};

export default ProgressRing;