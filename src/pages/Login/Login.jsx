import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Eye, EyeOff, Lock, Mail, Award, Shield, Star } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import logo from '../../assets/images/logo.png';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();
  const { login } = useAuth();

  async function handleLogin(e) {
    e.preventDefault();
    setIsLoading(true);
    setError('');
    
    try {
      const result = await login(email, password);
      
      if (result && result.success) {
        navigate('/dashboard');
      } else {
        setError(result?.error || 'Login failed');
      }
    } catch (err) {
      console.error('Login error:', err);
      setError('An unexpected error occurred. Please try again.');
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-secondary-50 flex items-center justify-center p-4">
      {/* Background Pattern */}
      <div className="absolute inset-0 bg-primary-100/20 opacity-50"></div>
      
      <div className="relative w-full max-w-6xl mx-auto grid lg:grid-cols-2 gap-8 items-center">
        {/* Left Side - Branding */}
        <div className="hidden lg:flex flex-col items-center justify-center text-center space-y-8">
          <div className="relative">
            <div className="absolute inset-0 bg-primary-200 rounded-full blur-3xl opacity-30"></div>
            <img
              src={logo}
              alt="Shree Anandhaas Logo"
              className="relative w-48 h-48 rounded-full shadow-glow border-8 border-white"
            />
          </div>
          
          <div className="space-y-4">
            <h1 className="text-5xl font-bold font-display text-primary-700 leading-tight">
              Shree Anandhaas
            </h1>
            <p className="text-2xl text-secondary-600 font-semibold">Premium Sweets & Snacks</p>
            <p className="text-lg text-neutral-600 max-w-md mx-auto leading-relaxed">
              Experience the finest traditional sweets crafted with love and premium ingredients since 1985
            </p>
          </div>
          
          <div className="grid grid-cols-3 gap-6 mt-8">
            <div className="text-center">
              <div className="w-16 h-16 bg-primary-100 rounded-2xl flex items-center justify-center mx-auto mb-3">
                <Award className="w-8 h-8 text-primary-600" />
              </div>
              <p className="text-sm font-semibold text-neutral-700">Premium Quality</p>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 bg-accent-100 rounded-2xl flex items-center justify-center mx-auto mb-3">
                <Shield className="w-8 h-8 text-accent-600" />
              </div>
              <p className="text-sm font-semibold text-neutral-700">Trusted Brand</p>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 bg-secondary-100 rounded-2xl flex items-center justify-center mx-auto mb-3">
                <Star className="w-8 h-8 text-secondary-600" />
              </div>
              <p className="text-sm font-semibold text-neutral-700">Customer Favorite</p>
            </div>
          </div>
        </div>
        
        {/* Right Side - Login Form */}
        <div className="flex items-center justify-center">
          <div className="w-full max-w-md">
            <div className="bg-white/80 backdrop-blur-md rounded-3xl shadow-strong border border-white/50 p-8">
              {/* Mobile Logo */}
              <div className="lg:hidden text-center mb-8">
                <img
                  src={logo}
                  alt="Shree Anandhaas Logo"
                  className="w-20 h-20 rounded-full mx-auto mb-4 shadow-medium"
                />
                <h2 className="text-2xl font-bold font-display text-primary-700">Shree Anandhaas</h2>
                <p className="text-secondary-600 font-semibold">Premium Sweets</p>
              </div>
              
              <div className="text-center mb-8">
                <h3 className="text-2xl font-bold text-neutral-800 font-brand mb-2">Welcome Back</h3>
                <p className="text-neutral-600">Sign in to access your dashboard</p>
              </div>
              
              <form onSubmit={handleLogin} className="space-y-6">
                {/* Email Field */}
                <div className="space-y-2">
                  <label className="text-sm font-semibold text-neutral-700">Email (@anandhaas only)</label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-neutral-400" />
                    <input
                      type="email"
                      placeholder="Enter your @anandhaas email"
                      value={email}
                      onChange={e => setEmail(e.target.value)}
                      className="w-full pl-12 pr-4 py-3 bg-neutral-50 border border-neutral-200 rounded-xl text-neutral-800 placeholder-neutral-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all duration-200"
                      required
                    />
                  </div>
                </div>
                
                {/* Password Field */}
                <div className="space-y-2">
                  <label className="text-sm font-semibold text-neutral-700">Password</label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-neutral-400" />
                    <input
                      type={showPassword ? 'text' : 'password'}
                      placeholder="Enter your password"
                      value={password}
                      onChange={e => setPassword(e.target.value)}
                      className="w-full pl-12 pr-12 py-3 bg-neutral-50 border border-neutral-200 rounded-xl text-neutral-800 placeholder-neutral-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all duration-200"
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 transform -translate-y-1/2 text-neutral-400 hover:text-neutral-600 transition-colors"
                    >
                      {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                    </button>
                  </div>
                </div>
                
                {/* Remember Me & Forgot Password */}
                <div className="flex items-center justify-between">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input type="checkbox" className="w-4 h-4 text-primary-600 border-neutral-300 rounded focus:ring-primary-500" />
                    <span className="text-sm text-neutral-600">Remember me</span>
                  </label>
                  <a href="#" className="text-sm text-primary-600 hover:text-primary-700 font-medium">Forgot password?</a>
                </div>
                
                {/* Error Message */}
                {error && (
                  <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl text-sm">
                    {error}
                  </div>
                )}
                
                {/* Login Button */}
                <button
                  type="submit"
                  disabled={isLoading}
                  className="w-full bg-gradient-to-r from-primary-500 to-primary-600 text-white py-3 rounded-xl font-semibold shadow-medium hover:from-primary-600 hover:to-primary-700 hover:shadow-strong focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isLoading ? (
                    <div className="flex items-center justify-center gap-2">
                      <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                      <span>Signing in...</span>
                    </div>
                  ) : (
                    'Sign In'
                  )}
                </button>
              </form>
              
              {/* Footer */}
              <div className="mt-8 text-center">
                <p className="text-sm text-neutral-500">
                  Don't have an account? 
                  <a href="#" className="text-primary-600 hover:text-primary-700 font-medium ml-1">Contact Admin</a>
                </p>
              </div>
            </div>
            
            {/* Security Notice */}
            <div className="mt-6 text-center">
              <p className="text-xs text-neutral-500 flex items-center justify-center gap-1">
                <Shield className="w-3 h-3" />
                Secured with enterprise-grade encryption
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
