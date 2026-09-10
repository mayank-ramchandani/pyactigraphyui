import React from "react";
import actilabLogo from "../assets/actilab-logo.png";

export default function BrandLogo({ width = 230, compact = false, style = {}, alt = "ActiLab — Actigraphy Data Processing" }) {
  return (
    <img
      src={actilabLogo}
      alt={alt}
      style={{
        width: compact ? Math.min(Number(width) || 230, 150) : width,
        maxWidth: "100%",
        height: "auto",
        objectFit: "contain",
        display: "block",
        background: "transparent",
        margin: "0 auto",
        borderRadius: 12,
        ...style,
      }}
    />
  );
}
