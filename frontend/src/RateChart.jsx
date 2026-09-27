import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceDot,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="chart-tooltip">
      <span>
        {new Date(`${label}T00:00:00`).toLocaleDateString('en', {
          month: 'short',
          day: 'numeric',
          year: 'numeric',
        })}
      </span>
      <strong>{Number(payload[0].value).toLocaleString('en', { maximumFractionDigits: 6 })}</strong>
    </div>
  );
}

export default function RateChart({ observations, source }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={observations} margin={{ top: 14, right: 16, bottom: 2, left: 0 }}>
        <CartesianGrid vertical={false} stroke="#e9eeea" strokeDasharray="3 5" />
        <XAxis
          dataKey="date"
          axisLine={false}
          tickLine={false}
          minTickGap={28}
          tick={{ fill: '#7c8780', fontSize: 11 }}
          tickFormatter={(value) => new Date(`${value}T00:00:00`).toLocaleDateString('en', {
            month: 'short',
            day: 'numeric',
          })}
        />
        <YAxis
          width={64}
          axisLine={false}
          tickLine={false}
          tick={{ fill: '#7c8780', fontSize: 11 }}
          domain={['auto', 'auto']}
          tickFormatter={(value) => Number(value).toLocaleString('en', { maximumFractionDigits: 4 })}
        />
        <Tooltip content={<ChartTooltip />} />
        <Line
          type="monotone"
          dataKey="rate"
          name={`1 ${source}`}
          stroke="#347454"
          strokeWidth={2.4}
          dot={observations.length === 1 ? { r: 4, fill: '#347454', stroke: '#fff', strokeWidth: 2 } : false}
          activeDot={{ r: 4, fill: '#347454', stroke: '#fff', strokeWidth: 2 }}
        />
        {observations.length === 1 && (
          <ReferenceDot
            x={observations[0].date}
            y={Number(observations[0].rate)}
            r={5}
            fill="#347454"
            stroke="#fff"
            strokeWidth={2}
          />
        )}
      </LineChart>
    </ResponsiveContainer>
  );
}