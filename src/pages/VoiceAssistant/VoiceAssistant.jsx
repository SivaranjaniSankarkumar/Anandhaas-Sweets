import sweetsBg from '../../assets/images/sweets-bg.webp';
import { Mic, Send, Volume2, BarChart3, PieChart, TrendingUp, Download, MessageSquare, Clock, User, Bot, FileText, Share2, Eye, EyeOff, X } from 'lucide-react';
import React, { useState, useRef, useEffect } from 'react';
import { BarChart, Bar, PieChart as RechartsPieChart, Pie, Cell, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useAuth } from '../../contexts/AuthContext';

const API_BASE = 'http://localhost:5001/api';
const COLORS = ['#1e40af', '#059669', '#d97706', '#dc2626', '#7c3aed', '#0891b2', '#65a30d', '#ea580c'];
const GRADIENT_COLORS = [
  { start: '#3b82f6', end: '#1e40af' },
  { start: '#10b981', end: '#059669' },
  { start: '#f59e0b', end: '#d97706' },
  { start: '#ef4444', end: '#dc2626' }
];

export default function VoiceAssistant() {
  const { user } = useAuth();
  const [transcript, setTranscript] = useState('');
  const [response, setResponse] = useState('');
  const [listening, setListening] = useState(false);
  const [chartData, setChartData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [textInput, setTextInput] = useState('');
  const [backendStatus, setBackendStatus] = useState('checking');
  const [slackSending, setSlackSending] = useState(false);
  const [slackMessage, setSlackMessage] = useState('');
  const [selectedChannel, setSelectedChannel] = useState('test_channel_1');
  const [slackChannels, setSlackChannels] = useState([
    {key: 'test_channel_1', name: 'Slack Test Channel 1'},
    {key: 'test_channel_2', name: 'Slack Test Channel 2'}
  ]);
  const [showUserQuery, setShowUserQuery] = useState(false);
  const [chatHistory, setChatHistory] = useState([]);
  
  // Load chat history when user is available
  useEffect(() => {
    if (user) {
      try {
        const userId = user?.username || user?.signInDetails?.loginId || 'authenticated_user';
        const storageKey = `anandhaas_sweets_chat_history_${userId}`;
        console.log('Loading chat history for user:', userId, 'with key:', storageKey);
        const saved = localStorage.getItem(storageKey);
        if (saved) {
          const parsed = JSON.parse(saved);
          const weekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
          const filteredHistory = parsed.filter(chat => new Date(chat.timestamp) > weekAgo).map(chat => ({
            ...chat,
            timestamp: new Date(chat.timestamp)
          }));
          console.log('Loaded chat history:', filteredHistory.length, 'items');
          setChatHistory(filteredHistory);
        } else {
          console.log('No saved chat history found');
        }
      } catch (error) {
        console.error('Error loading chat history:', error);
      }
    }
  }, [user]);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  // Check backend status on component mount
  useEffect(() => {
    checkBackendStatus();
    loadSlackChannels();
  }, []);

  async function loadSlackChannels() {
    try {
      const response = await fetch(`${API_BASE}/slack-channels`);
      if (response.ok) {
        const data = await response.json();
        setSlackChannels(data.channels);
      }
    } catch (error) {
      console.error('Failed to load Slack channels:', error);
    }
  }

  async function checkBackendStatus() {
    try {
      const response = await fetch(`${API_BASE}/dashboard-data`);
      if (response.ok) {
        setBackendStatus('connected');
      } else {
        setBackendStatus('error');
      }
    } catch (error) {
      setBackendStatus('error');
    }
  }

  async function handleStartListening() {
    try {
      setListening(true);
      setTranscript('Listening...');
      
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new MediaRecorder(stream);
      audioChunksRef.current = [];
      
      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };
      
      mediaRecorderRef.current.onstop = async () => {
        try {
          const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
          const formData = new FormData();
          formData.append('audio', audioBlob, 'audio.wav');
          
          console.log('Sending audio to backend...');
          const response = await fetch(`${API_BASE}/transcribe`, {
            method: 'POST',
            body: formData
          });
          
          console.log('Response status:', response.status);
          if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`HTTP ${response.status}: ${errorText}`);
          }
          
          const result = await response.json();
          console.log('Transcription result:', result);
          const transcribedText = result.transcript || 'Transcription failed';
          setTranscript(transcribedText);
          
          // Auto-send the transcribed query
          if (transcribedText && !transcribedText.includes('error') && !transcribedText.includes('failed')) {
            setTimeout(() => {
              handleSend(transcribedText);
            }, 500); // Small delay to ensure state is updated
          }
        } catch (error) {
          console.error('Transcription error:', error);
          setTranscript(`Transcription error: ${error.message}`);
        }
      };
      
      mediaRecorderRef.current.start(1000); // Record in 1-second chunks
    } catch (error) {
      console.error('Microphone error:', error);
      setListening(false);
      setTranscript('Microphone access denied');
    }
  }

  function handleStopListening() {
    setListening(false);
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
    }
  }

  async function handleSend(customQuery = null) {
    const query = customQuery || transcript || textInput;
    if (!query || query === 'Listening...' || loading) return;
    
    console.log('Sending query:', query);
    setLoading(true);
    setResponse('Processing your request...');
    
    try {
      const response = await fetch(`${API_BASE}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query })
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      const result = await response.json();
      console.log('Backend response:', result);
      
      const responseText = `${result.title} (${result.chart_type} chart with ${result.data?.length || 0} data points)`;
      setResponse(responseText);
      setChartData(result);
      
      // Add to chat history
      const newChat = {
        id: Date.now(),
        query: query,
        response: responseText,
        timestamp: new Date(),
        chartType: result.chart_type,
        chartData: result // Store complete chart data
      };
      
      setChatHistory(prev => {
        const updated = [...prev, newChat];
        // Save to localStorage with user-specific key
        try {
          const userId = user?.username || user?.signInDetails?.loginId || 'authenticated_user';
          const storageKey = `anandhaas_sweets_chat_history_${userId}`;
          console.log('Saving chat history for user:', userId, 'with key:', storageKey);
          localStorage.setItem(storageKey, JSON.stringify(updated));
        } catch (error) {
          console.error('Error saving chat history:', error);
        }
        return updated;
      });
      
      // Clear inputs after successful query
      if (textInput) {
        setTextInput('');
      }
    } catch (error) {
      setResponse(`Error: ${error.message}. Make sure backend is running on port 5001.`);
      console.error('Query error:', error);
    } finally {
      setLoading(false);
    }
  }

  function handleTextSubmit(e) {
    e.preventDefault();
    if (textInput.trim()) {
      setTranscript(textInput.trim());
      handleSend(textInput.trim());
    }
  }

  async function handleDownloadPDF() {
    if (!chartData || !chartData.pdf_base64) {
      alert('No PDF available to download');
      return;
    }
    
    try {
      const byteCharacters = atob(chartData.pdf_base64);
      const byteNumbers = new Array(byteCharacters.length);
      for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
      }
      const byteArray = new Uint8Array(byteNumbers);
      const blob = new Blob([byteArray], { type: 'application/pdf' });
      
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = chartData.pdf_filename || 'report.pdf';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('PDF download error:', error);
      alert('Failed to download PDF');
    }
  }

  async function handleSendToSlack() {
    if (!chartData || !chartData.pdf_base64) {
      alert('No report available to send');
      return;
    }
    
    setSlackSending(true);
    setSlackMessage('Sending to Slack...');
    
    try {
      const response = await fetch(`${API_BASE}/send-to-slack`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          channel: selectedChannel,
          pdf_base64: chartData.pdf_base64,
          filename: chartData.pdf_filename || 'report.pdf',
          title: chartData.title || 'Business Report',
          insights: chartData.insights || 'Analysis completed'
        })
      });
      
      const result = await response.json();
      
      if (result.success) {
        setSlackMessage('✅ Successfully sent to Slack!');
      } else {
        setSlackMessage(`❌ Failed: ${result.message}`);
      }
    } catch (error) {
      console.error('Slack send error:', error);
      setSlackMessage('❌ Failed to send to Slack');
    } finally {
      setSlackSending(false);
      setTimeout(() => setSlackMessage(''), 3000);
    }
  }

  function renderChart() {
    if (!chartData || !chartData.data) return null;
    
    const { chart_type, data, title, dual_metrics } = chartData;
    
    // Check if this is dual metrics (both revenue and count)
    const isDualMetrics = dual_metrics || (data.length > 0 && data[0].hasOwnProperty('revenue') && data[0].hasOwnProperty('count'));
    
    if (isDualMetrics) {
      return (
        <div className="mt-8 bg-gradient-to-br from-slate-50 to-white p-8 rounded-2xl shadow-2xl border border-slate-200">
          <h3 className="font-bold text-xl text-slate-800 mb-6 flex items-center gap-3">
            <div className="p-2 bg-blue-100 rounded-lg">
              <BarChart3 className="w-6 h-6 text-blue-600" />
            </div>
            {title}
          </h3>
          <div className="grid grid-cols-2 gap-8">
            <div>
              <h4 className="text-lg font-semibold text-slate-700 mb-4 text-center">Revenue Analysis</h4>
              <ResponsiveContainer width="100%" height={350}>
                <BarChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="2 2" stroke="#e2e8f0" strokeOpacity={0.5} />
                  <XAxis 
                    dataKey="name" 
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: '#64748b', fontSize: 11, fontWeight: 500 }}
                  />
                  <YAxis 
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: '#64748b', fontSize: 11, fontWeight: 500 }}
                  />
                  <Tooltip 
                    contentStyle={{
                      backgroundColor: '#1f2937',
                      border: 'none',
                      borderRadius: '12px',
                      color: '#ffffff',
                      boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)'
                    }}
                    formatter={(value) => [`₹${value.toLocaleString()}`, 'Revenue']}
                  />
                  <Bar dataKey="revenue" fill="#1e40af" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div>
              <h4 className="text-lg font-semibold text-slate-700 mb-4 text-center">Transaction Count</h4>
              <ResponsiveContainer width="100%" height={350}>
                <BarChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="2 2" stroke="#e2e8f0" strokeOpacity={0.5} />
                  <XAxis 
                    dataKey="name" 
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: '#64748b', fontSize: 11, fontWeight: 500 }}
                  />
                  <YAxis 
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: '#64748b', fontSize: 11, fontWeight: 500 }}
                  />
                  <Tooltip 
                    contentStyle={{
                      backgroundColor: '#1f2937',
                      border: 'none',
                      borderRadius: '12px',
                      color: '#ffffff',
                      boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)'
                    }}
                    formatter={(value) => [value, 'Count']}
                  />
                  <Bar dataKey="count" fill="#059669" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      );
    }
    
    if (chart_type === 'pie') {
      return (
        <div className="mt-6 bg-white p-4 rounded-xl shadow">
          <h3 className="font-semibold text-gold mb-4 flex items-center gap-2">
            <PieChart className="w-5 h-5" /> {title}
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <RechartsPieChart>
              <Pie dataKey="value" data={data} cx="50%" cy="50%" outerRadius={80} label>
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </RechartsPieChart>
          </ResponsiveContainer>
        </div>
      );
    }
    
    if (chart_type === 'line') {
      const isRevenue = chartData.y_axis === 'Total Amount';
      return (
        <div className="mt-6 bg-white p-4 rounded-xl shadow">
          <h3 className="font-semibold text-gold mb-4 flex items-center gap-2">
            <TrendingUp className="w-5 h-5" /> {title}
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Line type="monotone" dataKey="value" stroke="#2563eb" strokeWidth={3} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      );
    }
    
    const isRevenue = chartData.y_axis === 'Total Amount';
    return (
      <div className="mt-6 bg-white p-4 rounded-xl shadow">
        <h3 className="font-semibold text-gold mb-4 flex items-center gap-2">
          <BarChart3 className="w-5 h-5" /> {title}
        </h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="value" fill="#2563eb" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    );
  }

  const [isHistoryOpen, setIsHistoryOpen] = useState(false);

  return (
    <div className="min-h-screen relative">
      <div 
        className="fixed inset-0 bg-cover bg-center bg-no-repeat opacity-40 z-0"
        style={{ backgroundImage: `url(${sweetsBg})` }}
      />
      <div className="relative z-10 min-h-screen">
      {/* History Toggle Button */}
      <button
        onClick={() => setIsHistoryOpen(true)}
        className="fixed top-40 right-6 z-30 bg-white hover:bg-primary-50 text-primary-600 px-4 py-2 rounded-lg shadow-medium hover:shadow-strong transition-all duration-200 group flex items-center gap-2"
        title="View Chat History"
      >
        <Clock className="w-4 h-4 group-hover:scale-110 transition-transform" />
        <span className="text-sm font-medium">Chat History</span>
      </button>

      {/* Chat History Slide Panel */}
      {isHistoryOpen && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-30 z-40"
          onClick={() => setIsHistoryOpen(false)}
        />
      )}
      
      <div className={`fixed top-0 right-0 h-screen w-80 bg-white shadow-2xl z-50 transform transition-transform duration-300 flex flex-col ${
        isHistoryOpen ? 'translate-x-0' : 'translate-x-full'
      }`}>
        <div className="p-4 border-b border-neutral-200 flex items-center justify-between">
          <h3 className="font-semibold text-neutral-800 flex items-center gap-2">
            <Clock className="w-4 h-4" />
            Chat History
          </h3>
          <button onClick={() => setIsHistoryOpen(false)} className="p-1 hover:bg-neutral-100 rounded">
            <X className="w-4 h-4 text-neutral-500" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-3" style={{ maxHeight: 'calc(100vh - 60px)' }}>
          {chatHistory.length === 0 ? (
            <div className="text-center text-gray-500 text-sm mt-8">
              No conversations yet
            </div>
          ) : (
            chatHistory.slice().reverse().map((chat) => (
              <div key={chat.id} className="bg-gray-50 rounded-lg p-3 hover:bg-gray-100 transition-colors cursor-pointer"
                   onClick={() => {
                     setTranscript(chat.query);
                     setResponse(chat.response);
                     setChartData(chat.chartData);
                     setIsHistoryOpen(false);
                   }}>
                <div className="flex items-start gap-2 mb-2">
                  <User className="w-3 h-3 text-blue-600 mt-0.5 flex-shrink-0" />
                  <p className="text-xs text-gray-700 line-clamp-2">{chat.query}</p>
                </div>
                <div className="flex items-start gap-2 mb-2">
                  <Bot className="w-3 h-3 text-green-600 mt-0.5 flex-shrink-0" />
                  <p className="text-xs text-gray-600 line-clamp-1">{chat.response}</p>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-xs text-gray-400">
                    {new Date(chat.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                  </span>
                  <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
                    {chat.chartType}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className="p-8">
        <div className="max-w-4xl mx-auto">
      {/* Backend Status - Only show errors */}
      <div className="mb-4">
        {backendStatus === 'error' && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
            ⚠️ Backend not connected. Please start the Flask server: <code>cd backend && python app_v1.py</code>
          </div>
        )}
      </div>

      <section className="rounded-2xl shadow-xl bg-white p-8 mb-6">
        
        {/* Voice Input */}
        <div className="flex gap-2 items-center mb-6">
          <button
            className={`flex items-center gap-2 px-4 py-2 rounded-xl font-medium shadow 
              ${listening ? 'bg-accentGreen text-dark' : 'bg-primary-600 text-white'} 
              hover:bg-primary-700 transition-all`}
            onClick={listening ? handleStopListening : handleStartListening}
          >
            <Mic className="w-6 h-6" />
            {listening ? 'Listening...' : 'Start Voice Input'}
          </button>
        </div>

        {/* Text Input */}
        <form onSubmit={handleTextSubmit} className="mb-6">
          <label className="font-semibold text-primary-600 mb-2 block">Or type your query:</label>
          <div className="flex gap-2">
            <input
              type="text"
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              placeholder="Ask about revenue, branches, categories..."
              className="flex-1 p-3 border rounded-xl bg-cream font-medium"
            />
            <button
              type="submit"
              className={`px-4 py-2 rounded-xl font-medium shadow transition-all
                ${loading ? 'bg-gray-400 cursor-not-allowed' : 'bg-primary-600 text-white hover:bg-primary-700'}`}
              disabled={loading}
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
        </form>

        {/* Optional User Query Display */}
        {showUserQuery && (
          <div className="mb-4">
            <label className="font-semibold text-dark mb-1 block">You said:</label>
            <div className="p-3 border rounded-xl min-h-[48px] bg-cream font-medium">
              {chartData && chartData.english_query && chartData.english_query !== chartData.original_query ? chartData.english_query : transcript}
            </div>
          </div>
        )}
        
        <div className="flex items-center justify-between mb-2">
          <label className="font-semibold text-dark">Assistant Reply:</label>
          <button
            onClick={() => setShowUserQuery(!showUserQuery)}
            className="text-xs text-gray-500 hover:text-gray-700 flex items-center gap-1 px-2 py-1 rounded transition-colors"
          >
            <User className="w-3 h-3" />
            {showUserQuery ? 'Hide' : 'Show'} your query
          </button>
        </div>
        <div className="p-3 border rounded-xl min-h-[48px] bg-beige font-medium flex items-center gap-2">
          <Volume2 className="w-5 h-5 text-gold" />
          <span>{response}</span>
        </div>

        {/* PDF and Slack Actions */}
        {chartData && chartData.pdf_base64 && (
          <div className="mt-6 p-4 bg-slate-50 rounded-xl border">
            <h4 className="font-semibold text-slate-800 mb-3">Export Options</h4>
            <div className="flex gap-3 items-center flex-wrap">
              <button
                onClick={handleDownloadPDF}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
              >
                <Download className="w-4 h-4" />
                Download PDF Report
              </button>
              
              <div className="flex items-center gap-2">
                <select
                  value={selectedChannel}
                  onChange={(e) => setSelectedChannel(e.target.value)}
                  className="px-3 py-2 border border-gray-300 rounded-lg bg-white text-sm font-medium focus:outline-none focus:ring-2 focus:ring-green-500"
                >
                  {slackChannels.map(channel => (
                    <option key={channel.key} value={channel.key}>
                      {channel.name}
                    </option>
                  ))}
                </select>
                
                <button
                  onClick={handleSendToSlack}
                  disabled={slackSending}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
                    slackSending 
                      ? 'bg-gray-400 cursor-not-allowed' 
                      : 'bg-green-600 hover:bg-green-700'
                  } text-white`}
                >
                  <MessageSquare className="w-4 h-4" />
                  {slackSending ? 'Sending...' : 'Send to Slack'}
                </button>
              </div>
              
              {slackMessage && (
                <span className={`text-sm font-medium ${
                  slackMessage.includes('✅') ? 'text-green-600' : 'text-red-600'
                }`}>
                  {slackMessage}
                </span>
              )}
            </div>
          </div>
        )}

      </section>
      {renderChart()}
        </div>
      </div>
    </div>
    </div>
  );
}
