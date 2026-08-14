import React from 'react';

interface RadialGaugeProps {
  value: number;
  maxValue?: number;
  label: string;
  sublabel?: string;
  size?: number;
  strokeWidth?: number;
  color?: 'cyan' | 'blue' | 'emerald' | 'amber' | 'rose';
  unit?: string;
}

export const RadialGauge: React.FC<RadialGaugeProps> = ({
  value,
  maxValue = 100,
  label,
  sublabel,
  size = 130,
  strokeWidth = 9,
  color = 'cyan',
  unit = '%'
}) => {
  const radius = (size - strokeWidth * 2) / 2;
  const circumference = 2 * Math.PI * radius;
  const percentage = Math.min(100, Math.max(0, (value / maxValue) * 100));
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  const colorMap = {
    cyan: {
      stroke: '#06b6d4',
      glow: 'rgba(6, 182, 212, 0.4)',
      bg: 'rgba(6, 182, 212, 0.1)'
    },
    blue: {
      stroke: '#3b82f6',
      glow: 'rgba(59, 130, 246, 0.4)',
      bg: 'rgba(59, 130, 246, 0.1)'
    },
    emerald: {
      stroke: '#10b981',
      glow: 'rgba(16, 185, 129, 0.4)',
      bg: 'rgba(16, 185, 129, 0.1)'
    },
    amber: {
      stroke: '#f59e0b',
      glow: 'rgba(245, 158, 11, 0.4)',
      bg: 'rgba(245, 158, 11, 0.1)'
    },
    rose: {
      stroke: '#f43f5e',
      glow: 'rgba(244, 63, 94, 0.4)',
      bg: 'rgba(244, 63, 94, 0.1)'
    }
  };

  const scheme = colorMap[color];

  return (
    <div className="flex flex-col items-center justify-center p-3 relative">
      <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="transform -rotate-90">
          {/* Background Track */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke="rgba(255, 255, 255, 0.07)"
            strokeWidth={strokeWidth}
            fill="transparent"
          />
          {/* Active Glowing Arc */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke={scheme.stroke}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            fill="transparent"
            style={{
              filter: `drop-shadow(0 0 6px ${scheme.glow})`,
              transition: 'stroke-dashoffset 0.8s ease-in-out'
            }}
          />
        </svg>

        {/* Inner Metric Text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
          <div className="font-mono font-extrabold text-white tracking-tight flex items-baseline justify-center" style={{ fontSize: size * 0.18 }}>
            <span>{typeof value === 'number' ? (value % 1 === 0 ? value : value.toFixed(1)) : value}</span>
            <span className="text-[10px] text-slate-400 ml-0.5 font-sans font-semibold">{unit}</span>
          </div>
          {sublabel && (
            <span className="text-[9px] uppercase tracking-wider text-slate-400 font-mono mt-0.5">
              {sublabel}
            </span>
          )}
        </div>
      </div>

      <span className="text-xs font-semibold text-slate-200 mt-2 text-center tracking-tight">
        {label}
      </span>
    </div>
  );
};
