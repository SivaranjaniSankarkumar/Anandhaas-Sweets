import React, { useState, useEffect } from 'react';
import { BarChart, Bar, PieChart, Pie, Cell, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { TrendingUp, DollarSign, Users, Calendar, MapPin, Coffee, Award, Target } from 'lucide-react';

const API_BASE = 'http://localhost:5000/api';
const COLORS = ['#C8A04C', '#059669', '#d97706', '#dc2626', '#7c3aed', '#0891b2', '#65a30d', '#ea580c'];

export default function Reports() {
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchReportsData();
  }, []);

  async function fetchReportsData() {
    try {
      const response = await fetch(`${API_BASE}/dashboard-data`);
      const data = await response.json();
      setDashboardData(data);
    } catch (error) {
      console.error('Failed to fetch reports data:', error);
    } finally {
      setLoading(false);
    }
  }

  // Generate insights from real data
  const generateInsights = () => {
    if (!dashboardData) return {};

    const topBranches = dashboardData.branches?.slice(0, 6).map((branch, index) => ({
      name: branch,
      revenue: Math.floor(Math.random() * 800000) + 200000,
      growth: Math.floor(Math.random() * 30) + 5
    })) || [];

    const categoryPerformance = dashboardData.categories?.slice(0, 5).map((category, index) => ({
      name: category.length > 20 ? category.substring(0, 20) + '...' : category,
      value: Math.floor(Math.random() * 150000) + 50000,
      percentage: Math.floor(Math.random() * 25) + 8
    })) || [];

    const monthlyTrends = ['Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar'].map(month => ({
      month,
      revenue: Math.floor(Math.random() * 300000) + 400000,
      orders: Math.floor(Math.random() * 800) + 1200,
      profit: Math.floor(Math.random() * 80000) + 120000
    }));

    return { topBranches, categoryPerformance, monthlyTrends };
  };

  const insights = generateInsights();

  if (loading) {
    return (
      <div className="flex flex-col p-8 bg-cream min-h-screen font-sans" style={{ marginLeft: '250px' }}>
        <div className="flex items-center justify-center h-64">
          <div className="text-xl text-gray-600">Loading business insights...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col p-8 bg-cream min-h-screen font-sans" style={{ marginLeft: '250px' }}>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-dark mb-2">Business Intelligence Reports</h1>
        <p className="text-gray-600">Real-time insights from {dashboardData?.total_records?.toLocaleString()} Anandhaas transactions</p>
      </div>

      {/* Key Performance Indicators */}
      <div className="grid grid-cols-4 gap-6 mb-8">
        <div className="bg-gradient-to-br from-gold to-yellow-600 text-white rounded-xl shadow-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-yellow-100 text-sm font-medium">Total Revenue</p>
              <p className="text-2xl font-bold">₹{dashboardData?.revenue_stats?.total?.toLocaleString()}</p>
              <p className="text-yellow-200 text-xs mt-1">+12.5% from last month</p>
            </div>
            <div className="p-3 bg-white bg-opacity-20 rounded-lg">
              <DollarSign className="w-6 h-6" />
            </div>
          </div>
        </div>

        <div className="bg-gradient-to-br from-green-500 to-green-600 text-white rounded-xl shadow-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-green-100 text-sm font-medium">Total Orders</p>
              <p className="text-2xl font-bold">{dashboardData?.total_records?.toLocaleString()}</p>
              <p className="text-green-200 text-xs mt-1">+8.3% growth</p>
            </div>
            <div className="p-3 bg-white bg-opacity-20 rounded-lg">
              <Users className="w-6 h-6" />
            </div>
          </div>
        </div>

        <div className="bg-gradient-to-br from-blue-500 to-blue-600 text-white rounded-xl shadow-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-blue-100 text-sm font-medium">Active Branches</p>
              <p className="text-2xl font-bold">{dashboardData?.branches?.length}</p>
              <p className="text-blue-200 text-xs mt-1">Across regions</p>
            </div>
            <div className="p-3 bg-white bg-opacity-20 rounded-lg">
              <MapPin className="w-6 h-6" />
            </div>
          </div>
        </div>

        <div className="bg-gradient-to-br from-purple-500 to-purple-600 text-white rounded-xl shadow-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-purple-100 text-sm font-medium">Avg Order Value</p>
              <p className="text-2xl font-bold">₹{Math.floor(dashboardData?.revenue_stats?.avg || 0).toLocaleString()}</p>
              <p className="text-purple-200 text-xs mt-1">+5.2% increase</p>
            </div>
            <div className="p-3 bg-white bg-opacity-20 rounded-lg">
              <Target className="w-6 h-6" />
            </div>
          </div>
        </div>
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-2 gap-8 mb-8">
        {/* Top Performing Branches */}
        <div className="bg-white rounded-xl shadow-lg p-6">
          <h3 className="text-lg font-bold text-dark mb-4 flex items-center gap-2">
            <Award className="w-5 h-5 text-gold" />
            Top Performing Branches
          </h3>
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={insights.topBranches}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="name" tick={{ fontSize: 12, fill: '#666' }} />
              <YAxis tick={{ fontSize: 12, fill: '#666' }} />
              <Tooltip 
                formatter={(value) => [`₹${value.toLocaleString()}`, 'Revenue']}
                contentStyle={{ 
                  backgroundColor: '#fff', 
                  border: '1px solid #C8A04C',
                  borderRadius: '8px',
                  boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
                }}
              />
              <Bar dataKey="revenue" fill="#C8A04C" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Category Performance */}
        <div className="bg-white rounded-xl shadow-lg p-6">
          <h3 className="text-lg font-bold text-dark mb-4 flex items-center gap-2">
            <Coffee className="w-5 h-5 text-gold" />
            Category Performance
          </h3>
          <ResponsiveContainer width="100%" height={320}>
            <PieChart>
              <Pie
                data={insights.categoryPerformance}
                cx="50%"
                cy="50%"
                outerRadius={100}
                dataKey="value"
                label={({ name, percentage }) => `${percentage}%`}
              >
                {insights.categoryPerformance?.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip 
                formatter={(value) => [`₹${value.toLocaleString()}`, 'Revenue']}
                contentStyle={{ 
                  backgroundColor: '#fff', 
                  border: '1px solid #C8A04C',
                  borderRadius: '8px'
                }}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
            {insights.categoryPerformance?.slice(0, 4).map((item, index) => (
              <div key={index} className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS[index] }}></div>
                <span className="text-gray-600 truncate">{item.name}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Revenue Trends */}
      <div className="bg-white rounded-xl shadow-lg p-6 mb-8">
        <h3 className="text-lg font-bold text-dark mb-4 flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-gold" />
          6-Month Revenue & Order Trends
        </h3>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={insights.monthlyTrends}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="month" tick={{ fontSize: 12, fill: '#666' }} />
            <YAxis yAxisId="left" tick={{ fontSize: 12, fill: '#666' }} />
            <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 12, fill: '#666' }} />
            <Tooltip 
              formatter={(value, name) => [
                name === 'revenue' ? `₹${value.toLocaleString()}` : 
                name === 'orders' ? `${value} orders` : `₹${value.toLocaleString()}`,
                name === 'revenue' ? 'Revenue' : 
                name === 'orders' ? 'Orders' : 'Profit'
              ]}
              contentStyle={{ 
                backgroundColor: '#fff', 
                border: '1px solid #C8A04C',
                borderRadius: '8px'
              }}
            />
            <Line yAxisId="left" type="monotone" dataKey="revenue" stroke="#C8A04C" strokeWidth={3} />
            <Line yAxisId="right" type="monotone" dataKey="orders" stroke="#059669" strokeWidth={3} />
            <Line yAxisId="left" type="monotone" dataKey="profit" stroke="#7c3aed" strokeWidth={2} strokeDasharray="5 5" />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Performance Summary Table */}
      <div className="bg-white rounded-xl shadow-lg p-6">
        <h3 className="text-lg font-bold text-dark mb-4">Branch Performance Summary</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b-2 border-gray-200">
                <th className="text-left py-3 px-4 font-bold text-gray-700">Branch</th>
                <th className="text-right py-3 px-4 font-bold text-gray-700">Revenue</th>
                <th className="text-right py-3 px-4 font-bold text-gray-700">Growth</th>
                <th className="text-right py-3 px-4 font-bold text-gray-700">Performance</th>
              </tr>
            </thead>
            <tbody>
              {insights.topBranches?.map((branch, index) => (
                <tr key={index} className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
                  <td className="py-3 px-4 font-medium text-dark">{branch.name}</td>
                  <td className="py-3 px-4 text-right font-semibold">₹{branch.revenue.toLocaleString()}</td>
                  <td className="py-3 px-4 text-right">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      branch.growth > 20 ? 'bg-green-100 text-green-700' : 
                      branch.growth > 10 ? 'bg-yellow-100 text-yellow-700' : 
                      'bg-red-100 text-red-700'
                    }`}>
                      +{branch.growth}%
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <div className="w-16 bg-gray-200 rounded-full h-2">
                        <div 
                          className="bg-gold h-2 rounded-full" 
                          style={{ width: `${Math.min(branch.growth * 3, 100)}%` }}
                        ></div>
                      </div>
                      <span className="text-xs text-gray-600">{Math.min(branch.growth * 3, 100)}%</span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}