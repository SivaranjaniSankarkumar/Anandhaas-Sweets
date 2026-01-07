import { LayoutDashboard, Mic, Shield, Award, TrendingUp, Users, Settings, HelpCircle, ExternalLink } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import logo from '../../assets/images/logo.png';

export default function Sidebar() {
  const location = useLocation();
  const activePath = location.pathname;

  const NavItem = ({ to, icon: Icon, children, badge }) => (
    <Link
      to={to}
      className={`group relative flex items-center gap-3 rounded-xl py-3 px-4 font-medium transition-all duration-200 ${
        activePath === to || (to === '/dashboard' && activePath === '/')
          ? 'bg-gradient-to-r from-primary-500 to-primary-600 text-white shadow-medium'
          : 'text-neutral-600 hover:bg-primary-50 hover:text-primary-700'
      }`}
    >
      <Icon className={`w-5 h-5 transition-transform duration-200 ${
        activePath === to || (to === '/dashboard' && activePath === '/')
          ? 'text-white'
          : 'text-neutral-500 group-hover:text-primary-600'
      }`} />
      <span className="font-medium">{children}</span>
      {badge && (
        <span className="ml-auto bg-primary-100 text-primary-700 text-xs px-2 py-1 rounded-full font-semibold">
          {badge}
        </span>
      )}
      {(activePath === to || (to === '/dashboard' && activePath === '/')) && (
        <div className="absolute left-0 top-0 bottom-0 w-1 bg-white rounded-r-full"></div>
      )}
    </Link>
  );

  return (
    <aside className="fixed left-0 top-0 h-full w-[280px] bg-white shadow-strong flex flex-col z-30 border-r border-neutral-100">
      {/* Enhanced Logo and Brand Section */}
      <div className="flex flex-col items-center pt-8 pb-6 px-6 border-b border-neutral-100">
        <div className="relative mb-4">
          <div className="absolute inset-0 bg-primary-100 rounded-full blur-xl opacity-50"></div>
          <img
            src={logo}
            alt="Shree Anandhaas Logo"
            className="relative w-24 h-24 rounded-full shadow-medium border-4 border-primary-100"
            draggable={false}
            style={{ objectFit: 'contain' }}
          />
        </div>
        <div className="text-center">
          <h1 className="text-primary-700 font-bold text-xl font-display leading-tight">
            Shree Anandhaas
          </h1>
          <p className="text-secondary-600 font-semibold text-sm">Premium Sweets</p>
          <div className="flex items-center justify-center gap-1 mt-2">
            <Award className="w-3 h-3 text-primary-500" />
            <span className="text-xs text-neutral-500 font-medium">Since 1985</span>
          </div>
        </div>
      </div>

      {/* Navigation Menu */}
      <nav className="flex-1 flex flex-col gap-2 px-6 py-6">
        <div className="mb-4">
          <h3 className="text-xs font-semibold text-neutral-400 uppercase tracking-wider mb-3">Main Menu</h3>
          <div className="space-y-1">
            <NavItem to="/quicksuite" icon={ExternalLink}>
              QuickSuite
            </NavItem>
            <NavItem to="/voice-assistant" icon={Mic}>
              Voice Assistant
            </NavItem>
          </div>
        </div>

        <div>
          <h3 className="text-xs font-semibold text-neutral-400 uppercase tracking-wider mb-3">Support</h3>
          <div className="space-y-1">
            <NavItem to="/settings" icon={Settings}>
              Settings
            </NavItem>
            <NavItem to="/help" icon={HelpCircle}>
              Help Center
            </NavItem>
          </div>
        </div>
      </nav>

      {/* Enhanced Wickr Button */}
      <div className="p-6 border-t border-neutral-100">
        <button className="w-full flex items-center gap-3 bg-gradient-to-r from-neutral-800 to-neutral-900 text-white rounded-xl py-3 px-4 font-medium hover:from-neutral-700 hover:to-neutral-800 transition-all duration-200 shadow-medium hover:shadow-strong group">
          <Shield className="w-5 h-5 -rotate-12 group-hover:rotate-0 transition-transform duration-200" />
          <span>Secure Chat</span>
          <div className="ml-auto w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
        </button>
        
        {/* Status Indicator */}
        <div className="mt-4 flex items-center justify-center gap-2 text-xs text-neutral-500">
          <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
          <span>System Online</span>
        </div>
      </div>
    </aside>
  );
}
