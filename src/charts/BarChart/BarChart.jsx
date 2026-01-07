import { BarChart, Bar, CartesianGrid, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

const data = [
  { sweet: 'Ladoo', count: 180 },
  { sweet: 'Mysore Pak', count: 130 },
];

export default function PopularSweetsBarChart() {
  return (
    <ResponsiveContainer width="100%" height={160}>
      <BarChart data={data} margin={{ top: 18, right: 10, left: -10, bottom: 0 }}>
        <CartesianGrid stroke="#eee" vertical={false} />
        <XAxis dataKey="sweet" stroke="#999" />
        <YAxis stroke="#999" domain={[0, 200]} />
        <Tooltip />
        <Bar dataKey="count" fill="#C8A04C" radius={[6, 6, 6, 6]}>
          {data.map((entry, index) => (
            <cell key={`cell-${index}`} fill={index === 1 ? "#C9D68D" : "#C8A04C"} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
