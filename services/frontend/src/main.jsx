import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import { TimezoneProvider } from './hooks/useTimezone';
import './styles/global.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <TimezoneProvider>
      <App />
    </TimezoneProvider>
  </React.StrictMode>
);
