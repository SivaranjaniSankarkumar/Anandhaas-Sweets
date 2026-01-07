import { User, Settings, LogOut, Calendar, Clock } from 'lucide-react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';

export default function Navbar() {
  const location = useLocation();
  const navigate = useNavigate();
  const { logout, user } = useAuth();
  const [showUserMenu, setShowUserMenu] = useState(false);


  const handleLogout = async () => {
    await logout();
    navigate('/');
  };

  const currentTime = new Date().toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: true
  });

  const currentDate = new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });

  return (
    <nav className="w-full bg-white/80 backdrop-blur-md border-b border-neutral-200 px-8 py-4 font-sans sticky top-0 z-20">
      <div className="flex items-center justify-between">
        {/* Left Section - Page Info */}
        <div className="flex items-center gap-4">
          <div>
            <h2 className="text-xl font-semibold text-primary-600 font-brand">
              {location.pathname === '/dashboard' || location.pathname === '/' ? 'Dashboard Overview' :
               location.pathname === '/voice-assistant' ? 'Anandhaas AI Assistant' :
               location.pathname === '/quicksuite' ? 'QuickSuite Dashboard' :
               location.pathname === '/reports' ? 'Sales Reports' :
               location.pathname === '/customers' ? 'Customer Management' :
               'Anandhaas Dashboard'}
            </h2>
            <div className="flex items-center gap-4 text-sm text-primary-500 mt-1">
              <div className="flex items-center gap-1">
                <Calendar className="w-4 h-4" />
                <span>{currentDate}</span>
              </div>
              <div className="flex items-center gap-1">
                <Clock className="w-4 h-4" />
                <span>{currentTime}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Section - Actions */}
        <div className="flex items-center gap-4">
          {/* User Menu */}
          <div className="relative">
            <button
              onClick={() => setShowUserMenu(!showUserMenu)}
              className="flex items-center gap-3 p-2 rounded-xl bg-gradient-to-r from-primary-500 to-primary-600 text-white hover:from-primary-600 hover:to-primary-700 transition-all duration-200 shadow-medium"
            >
              <div className="w-8 h-8 bg-white/20 rounded-lg flex items-center justify-center">
                <User className="w-4 h-4" />
              </div>
              <div className="text-left">
                <p className="text-sm font-medium capitalize">{user?.signInDetails?.loginId?.split('@')[0] || 'Admin'}</p>
                <p className="text-xs opacity-90">Anandhaas Team</p>
              </div>
            </button>
            
            {showUserMenu && (
              <div className="absolute right-0 top-12 w-48 bg-white rounded-xl shadow-strong border border-neutral-200 py-2 z-50">
                <Link
                  to="/profile"
                  className="flex items-center gap-3 px-4 py-2 hover:bg-neutral-50 text-neutral-700 hover:text-primary-600 transition-colors"
                >
                  <User className="w-4 h-4" />
                  <span className="text-sm">Profile</span>
                </Link>
                <Link
                  to="/settings"
                  className="flex items-center gap-3 px-4 py-2 hover:bg-neutral-50 text-neutral-700 hover:text-primary-600 transition-colors"
                >
                  <Settings className="w-4 h-4" />
                  <span className="text-sm">Settings</span>
                </Link>
                <hr className="my-2 border-neutral-200" />
                <button
                  onClick={handleLogout}
                  className="flex items-center gap-3 px-4 py-2 hover:bg-red-50 text-red-600 transition-colors w-full text-left"
                >
                  <LogOut className="w-4 h-4" />
                  <span className="text-sm">Logout</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}
