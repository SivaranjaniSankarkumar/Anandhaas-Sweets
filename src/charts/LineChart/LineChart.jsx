import { LineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

const data = [
  { name: 'Jan', sales: 15 },
  { name: 'Feb', sales: 40 },
  { name: 'Mar', sales: 80 },
  { name: 'Apr', sales: 120 },
  { name: 'May', sales: 100 },
  { name: 'Jun', sales: 170 },
];

export default function SalesLineChart() {
  return (
    <ResponsiveContainer width="100%" height={160}>
      <LineChart data={data} margin={{ top: 18, right: 10, left: -10, bottom: 0 }}>
        <CartesianGrid stroke="#eee" vertical={false} />
        <XAxis dataKey="name" stroke="#999" />
        <YAxis stroke="#999" domain={[0, 200]} />
        <Tooltip />
        <Line type="monotone" dataKey="sales" stroke="#C8A04C" strokeWidth={3} dot={{ r: 2 }} />
      </LineChart>
    </ResponsiveContainer>
  );
}
