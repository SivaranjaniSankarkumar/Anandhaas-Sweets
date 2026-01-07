/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Primary Brand Colors - Anandhaas Theme
        primary: {
          50: '#E6F7F3',
          100: '#CCEFE7',
          200: '#99DFCF',
          300: '#66CFB7',
          400: '#33BF9F',
          500: '#009972', // Main Anandhaas green
          600: '#007A5B',
          700: '#005B44',
          800: '#003D2E',
          900: '#001E17'
        },
        secondary: {
          50: '#FDF6F5',
          100: '#FBEDEB',
          200: '#F7DBD7',
          300: '#F3C9C3',
          400: '#EFB7AF',
          500: '#ED6D5F', // Anandhaas coral/orange
          600: '#E94A38',
          700: '#C73E31',
          800: '#A5322A',
          900: '#832623'
        },
        accent: {
          50: '#F0F9F0',
          100: '#E1F3E1',
          200: '#C3E7C3',
          300: '#A5DBA5',
          400: '#87CF87',
          500: '#228B22', // Forest green
          600: '#1E7A1E',
          700: '#1A691A',
          800: '#165816',
          900: '#124712'
        },
        neutral: {
          50: '#FAFAFA',
          100: '#F5F5F5',
          200: '#E5E5E5',
          300: '#D4D4D4',
          400: '#A3A3A3',
          500: '#737373',
          600: '#525252',
          700: '#404040',
          800: '#262626',
          900: '#171717'
        },
        // Legacy colors for compatibility
        gold: '#009972', // Updated to Anandhaas green
        cream: '#FFFFFF',
        dark: '#262626',
        beige: '#F3D5A5',
        accentGreen: '#009972',
        anandhaasGreen: '#009972',
        anandhaasOrange: '#ED6D5F'
      },
      fontFamily: {
        'sans': ['Inter', 'system-ui', 'sans-serif'],
        'display': ['Playfair Display', 'serif'],
        'brand': ['Poppins', 'sans-serif']
      },
      boxShadow: {
        'soft': '0 2px 15px -3px rgba(0, 0, 0, 0.07), 0 10px 20px -2px rgba(0, 0, 0, 0.04)',
        'medium': '0 4px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 30px -5px rgba(0, 0, 0, 0.04)',
        'strong': '0 10px 40px -10px rgba(0, 0, 0, 0.15), 0 20px 50px -10px rgba(0, 0, 0, 0.1)',
        'glow': '0 0 20px rgba(212, 175, 55, 0.3)'
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'pulse-soft': 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite'
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' }
        },
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' }
        }
      }
    },
  },
  plugins: [],
}