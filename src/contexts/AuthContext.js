import { createContext, useContext, useState, useEffect } from 'react';
import { signIn, signOut, getCurrentUser, confirmSignIn } from 'aws-amplify/auth';

const AuthContext = createContext();

export function useAuth() {
  return useContext(AuthContext);
}

export function AuthProvider({ children }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAuthState();
  }, []);

  const checkAuthState = async () => {
    // Clear all AWS Amplify tokens first to prevent conflicts
    try {
      await signOut({ global: true });
    } catch (error) {
      // Ignore signOut errors
    }
    
    // Clear all Cognito tokens from localStorage
    Object.keys(localStorage).forEach(key => {
      if (key.startsWith('CognitoIdentityServiceProvider') || key.startsWith('aws-amplify')) {
        localStorage.removeItem(key);
      }
    });
    
    // Check if user was previously authenticated
    const wasAuthenticated = localStorage.getItem('anandhaas_sweets_auth_state');
    
    if (wasAuthenticated === 'true') {
      setIsAuthenticated(true);
      setUser({ username: 'authenticated_user' });
    } else {
      setIsAuthenticated(false);
      setUser(null);
    }
    
    setLoading(false);
  };

  const login = async (email, password) => {
    try {
      if (!email.includes('@anandhaas')) {
        return { success: false, error: 'Only @anandhaas email addresses are allowed' };
      }

      const result = await signIn({ 
        username: email, 
        password: password
      });
      
      if (result.isSignedIn) {
        const currentUser = await getCurrentUser();
        setUser(currentUser);
        setIsAuthenticated(true);
        localStorage.setItem('anandhaas_sweets_auth_state', 'true');
        return { success: true };
      } else if (result.nextStep?.signInStep === 'CONFIRM_SIGN_IN_WITH_NEW_PASSWORD_REQUIRED') {
        const confirmResult = await confirmSignIn({ 
          challengeResponse: password
        });
        
        if (confirmResult.isSignedIn) {
          const currentUser = await getCurrentUser();
          setUser(currentUser);
          setIsAuthenticated(true);
          localStorage.setItem('anandhaas_sweets_auth_state', 'true');
          return { success: true };
        }
      }
      
      return { success: false, error: 'Authentication failed' };
    } catch (error) {
      let errorMessage = 'Login failed';
      
      if (error.name === 'NotAuthorizedException') {
        errorMessage = 'Invalid email or password';
      } else if (error.name === 'UserNotFoundException') {
        errorMessage = 'User not found';
      } else if (error.message) {
        errorMessage = error.message;
      }
      
      return { success: false, error: errorMessage };
    }
  };

  const forceLogout = () => {
    // Force clear all authentication data without API calls
    setIsAuthenticated(false);
    setUser(null);
    
    // Clear auth state
    localStorage.removeItem('anandhaas_sweets_auth_state');
    
    // Clear only AWS Amplify related storage, preserve chat history
    Object.keys(localStorage).forEach(key => {
      if (key.startsWith('CognitoIdentityServiceProvider') || key.startsWith('aws-amplify')) {
        localStorage.removeItem(key);
      }
    });
    sessionStorage.clear();
    
    // Clear IndexedDB if it exists (Amplify sometimes uses it)
    if (window.indexedDB) {
      const deleteReq = indexedDB.deleteDatabase('amplify-datastore');
      deleteReq.onsuccess = () => console.log('Amplify datastore cleared');
    }
    
    // Reload the page to ensure clean state
    window.location.reload();
  };

  const logout = async () => {
    try {
      await signOut({ global: true }); // Sign out from all devices
      setIsAuthenticated(false);
      setUser(null);
      
      // Clear auth state
      localStorage.removeItem('anandhaas_sweets_auth_state');
      
      // Clear only AWS Amplify keys, preserve chat history
      Object.keys(localStorage).forEach(key => {
        if (key.startsWith('aws-amplify') || key.startsWith('CognitoIdentityServiceProvider')) {
          localStorage.removeItem(key);
        }
      });
      sessionStorage.clear();
      
    } catch (error) {
      console.error('Logout error:', error);
      // Force clear even if signOut fails
      forceLogout();
    }
  };

  const value = {
    isAuthenticated,
    user,
    loading,
    login,
    logout,
    forceLogout
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}