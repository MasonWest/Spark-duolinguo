import type { FC } from "react";

type Variant = "primary" | "success" | "warning" | "review" | "neutral";
type Size = "sm" | "md";

interface Props {
  variant: Variant;
  size?: Size;
  children: React.ReactNode;
  className?: string;
}

const Badge: FC<Props> = ({ variant, size = "md", children, className = "" }) => {
  const variantClass = `badge-${variant}`;
  const sizeClass = size === "sm" ? "badge-sm" : "";

  return (
    <span className={`badge ${variantClass} ${sizeClass} ${className}`}>
      {children}
    </span>
  );
};

export default Badge;