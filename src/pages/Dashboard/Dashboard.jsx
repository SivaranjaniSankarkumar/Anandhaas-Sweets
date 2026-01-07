import SalesLineChart from '../../charts/LineChart/LineChart';
import PopularSweetsBarChart from '../../charts/BarChart/BarChart';
import sweetsImage from '../../assets/images/sweets.png';
import { useState, useEffect } from 'react';
import { TrendingUp, Users, MapPin, Award, ShoppingBag, Clock, Star, BarChart3 } from 'lucide-react';

const API_BASE = 'http://localhost:5001/api';

export default function Dashboard() {
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  async function fetchDashboardData() {
    try {
      const response = await fetch(`${API_BASE}/dashboard-data`);
      const data = await response.json();
      setDashboardData(data);
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    } finally {
      setLoading(false);
    }
  }

  const MetricCard = ({ title, value, icon: Icon, gradient, textColor = "text-white", trend }) => (
    <div className={`relative overflow-hidden rounded-2xl ${gradient} p-6 shadow-medium hover:shadow-strong transition-all duration-300 group`}>
      <div className="relative z-10">
        <div className="flex items-center justify-between mb-4">
          <div className={`p-3 rounded-xl bg-white/20 backdrop-blur-sm`}>
            <Icon className="w-6 h-6 text-white" />
          </div>
          {trend && (
            <div className="flex items-center gap-1 text-white/90 text-sm">
              <TrendingUp className="w-4 h-4" />
              <span>+{trend}%</span>
            </div>
          )}
        </div>
        <div className={`${textColor} font-medium text-sm opacity-90 mb-1`}>{title}</div>
        <div className={`${textColor} text-3xl font-bold font-brand`}>
          {loading ? (
            <div className="animate-pulse bg-white/20 h-8 w-24 rounded"></div>
          ) : (
            value
          )}
        </div>
      </div>
      <div className="absolute inset-0 bg-gradient-to-br from-white/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
    </div>
  );

  const ChartCard = ({ title, subtitle, children, icon: Icon }) => (
    <div className="bg-white rounded-2xl shadow-soft hover:shadow-medium transition-all duration-300 overflow-hidden group">
      <div className="p-6 border-b border-neutral-100">
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2 rounded-lg bg-primary-50">
            <Icon className="w-5 h-5 text-primary-600" />
          </div>
          <div>
            <h3 className="font-semibold text-neutral-800 font-brand">{title}</h3>
            {subtitle && <p className="text-sm text-neutral-500">{subtitle}</p>}
          </div>
        </div>
      </div>
      <div className="p-6">
        {children}
      </div>
    </div>
  );

  return (
    <div className="flex flex-col p-8 bg-gradient-to-br from-neutral-50 to-primary-50/30 min-h-screen font-sans animate-fade-in">
      {/* Enhanced Hero Section */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-primary-600 via-primary-500 to-secondary-500 p-8 mb-8 shadow-strong">
        <div className="absolute inset-0 bg-white/5 opacity-30"></div>
        
        <div className="relative z-10 flex items-center justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-3 rounded-xl bg-white/20 backdrop-blur-sm">
                <Award className="w-8 h-8 text-white" />
              </div>
              <div>
                <h1 className="text-4xl font-bold text-white font-display leading-tight">
                  Shree Anandhaas Sweets
                </h1>
                <p className="text-white/90 text-lg font-medium">Premium Sweets & Snacks Dashboard</p>
              </div>
            </div>
            <div className="flex items-center gap-6 text-white/80">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4" />
                <span className="text-sm">Real-time Analytics</span>
              </div>
              <div className="flex items-center gap-2">
                <Star className="w-4 h-4" />
                <span className="text-sm">Premium Quality</span>
              </div>
            </div>
          </div>
          
          <div className="relative">
            <div className="absolute inset-0 bg-white/20 rounded-full blur-xl"></div>
            <img
              src={sweetsImage}
              alt="Premium Anandhaas Sweets"
              className="relative w-40 h-40 rounded-full shadow-glow object-cover border-4 border-white/30"
            />
          </div>
        </div>
      </div>

      {/* Enhanced Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <MetricCard
          title="Total Revenue"
          value={loading ? '...' : `₹${dashboardData?.revenue_stats?.total?.toLocaleString() || '2,45,680'}`}
          icon={TrendingUp}
          gradient="bg-gradient-to-br from-primary-500 to-primary-600"
          trend="12.5"
        />
        <MetricCard
          title="Total Orders"
          value={loading ? '...' : dashboardData?.total_records?.toLocaleString() || '1,247'}
          icon={ShoppingBag}
          gradient="bg-gradient-to-br from-accent-500 to-accent-600"
          trend="8.2"
        />
        <MetricCard
          title="Active Branches"
          value={loading ? '...' : dashboardData?.branches?.length || '12'}
          icon={MapPin}
          gradient="bg-gradient-to-br from-secondary-500 to-secondary-600"
          trend="5.1"
        />
        <MetricCard
          title="Happy Customers"
          value={loading ? '...' : '15,420'}
          icon={Users}
          gradient="bg-gradient-to-br from-primary-400 to-secondary-500"
          trend="15.3"
        />
      </div>

      {/* Enhanced Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        <ChartCard
          title="Sales Analytics"
          subtitle="Real-time revenue tracking"
          icon={BarChart3}
        >
          <SalesLineChart />
        </ChartCard>
        
        <ChartCard
          title="Popular Items"
          subtitle="Top-selling sweets & snacks"
          icon={Star}
        >
          <PopularSweetsBarChart />
        </ChartCard>
      </div>

      {/* Quick Stats Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white rounded-2xl p-6 shadow-soft hover:shadow-medium transition-all duration-300">
          <div className="flex items-center gap-4">
            <div className="p-3 rounded-xl bg-primary-100">
              <Award className="w-6 h-6 text-primary-600" />
            </div>
            <div>
              <h3 className="font-semibold text-neutral-800 font-brand">Quality Assured</h3>
              <p className="text-sm text-neutral-500">Premium ingredients & traditional recipes</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white rounded-2xl p-6 shadow-soft hover:shadow-medium transition-all duration-300">
          <div className="flex items-center gap-4">
            <div className="p-3 rounded-xl bg-accent-100">
              <Clock className="w-6 h-6 text-accent-600" />
            </div>
            <div>
              <h3 className="font-semibold text-neutral-800 font-brand">Fresh Daily</h3>
              <p className="text-sm text-neutral-500">Made fresh every morning</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white rounded-2xl p-6 shadow-soft hover:shadow-medium transition-all duration-300">
          <div className="flex items-center gap-4">
            <div className="p-3 rounded-xl bg-secondary-100">
              <Star className="w-6 h-6 text-secondary-600" />
            </div>
            <div>
              <h3 className="font-semibold text-neutral-800 font-brand">Customer Favorite</h3>
              <p className="text-sm text-neutral-500">4.8★ average rating</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
