import React, { useState, useEffect } from 'react';
import axios from 'axios';
import Login from './Login';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [userInfo, setUserInfo] = useState(null);
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Check if user is already authenticated on mount
  useEffect(() => {
    const token = localStorage.getItem('access_token');
    const storedUserInfo = localStorage.getItem('user_info');
    
    if (token && storedUserInfo) {
      try {
        const parsedUserInfo = JSON.parse(storedUserInfo);
        setUserInfo(parsedUserInfo);
        setIsAuthenticated(true);
      } catch (err) {
        // Invalid stored data, clear it
        localStorage.removeItem('access_token');
        localStorage.removeItem('user_info');
      }
    }
  }, []);

  const handleLoginSuccess = (data) => {
    setUserInfo({
      username: data.username,
      location: data.location,
      full_name: data.full_name
    });
    setIsAuthenticated(true);
  };

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_info');
    setIsAuthenticated(false);
    setUserInfo(null);
    setEvents([]);
    setError('');
    setSuccess('');
  };

  const handleSearch = async () => {
    setLoading(true);
    setError('');
    setSuccess('');
    setEvents([]);

    try {
      const token = localStorage.getItem('access_token');
      
      if (!token) {
        setError('Not authenticated. Please log in again.');
        handleLogout();
        return;
      }

      const response = await axios.get('/api/events/family', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      const data = response.data;

      if (data.error) {
        setError(data.error);
      } else if (data.success && data.events) {
        setEvents(data.events);
        const facebookCount = data.events.filter(e => e.source && e.source.includes('Facebook')).length;
        const macaroniCount = data.events.filter(e => e.source === 'MacaroniKID').length;
        const schoolsCount = data.events.filter(e => e.source && e.source.includes('Schools')).length;
        const churchesCount = data.events.filter(e => e.category === 'church' || (e.source && e.source.includes('church'))).length;
        let successMsg = `Found ${data.events.length} family events near ${userInfo.location}`;
        
        // Build source counts message
        const sourceCounts = [];
        if (facebookCount > 0) sourceCounts.push(`${facebookCount} Facebook`);
        if (macaroniCount > 0) sourceCounts.push(`${macaroniCount} MacaroniKID`);
        if (schoolsCount > 0) sourceCounts.push(`${schoolsCount} Schools`);
        if (churchesCount > 0) sourceCounts.push(`${churchesCount} Churches`);
        
        if (sourceCounts.length > 0) {
          successMsg += ` (${sourceCounts.join(', ')})`;
        }
        setSuccess(successMsg);
      } else {
        setError('No family events found.');
      }
    } catch (err) {
      if (err.response && err.response.status === 401) {
        setError('Session expired. Please log in again.');
        handleLogout();
      } else {
        setError(`Failed to fetch events: ${err.message}`);
      }
    } finally {
      setLoading(false);
    }
  };

  // If not authenticated, show login screen
  if (!isAuthenticated) {
    return <Login onLoginSuccess={handleLoginSuccess} />;
  }

  return (
    <div className="container">
      <div className="header">
        <div className="header-content">
          <div>
            <h1>SteviB's AI Outreach</h1>
            <p className="user-info">
              Welcome, <strong>{userInfo.full_name}</strong> | Location: <strong>{userInfo.location}</strong>
            </p>
          </div>
          <button className="btn btn-logout" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </div>

      <div className="controls">
        <div className="form-row">
          <div className="location-display">
            <label>Your Location</label>
            <div className="location-badge">{userInfo.location}</div>
          </div>

          <button
            className="btn"
            onClick={handleSearch}
            disabled={loading}
          >
            {loading ? 'Searching...' : 'Find Family Events'}
          </button>
        </div>
      </div>

      {error && <div className="error">{error}</div>}
      {success && <div className="success">{success}</div>}

      {loading && <div className="loading">Searching for family-focused events...</div>}

      {events.length > 0 && (
        <div className="events-container">
          {/* Facebook Events Table */}
          {events.filter(event => event.source && event.source.includes('Facebook')).length > 0 && (
            <div className="events-table">
              <div className="table-header">
                <h2>Facebook Events ({events.filter(event => event.source && event.source.includes('Facebook')).length})</h2>
              </div>
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>Event</th>
                      <th>When</th>
                      <th>Interest</th>
                      <th>Website</th>
                    </tr>
                  </thead>
                  <tbody>
                    {events.filter(event => event.source && event.source.includes('Facebook')).map((event, index) => (
                      <tr key={`facebook-${index}`}>
                        <td className="event-title">
                          {event.title || 'Untitled Event'}
                        </td>
                        <td className="event-meta">{event.when || 'N/A'}</td>
                        <td className="event-meta">{`${event.interested_count || 0} interested / ${event.attending_count || 0} going`}</td>
                        <td>
                          {event.website ? (
                            <a
                              href={event.website}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="event-website"
                            >
                              Visit Website
                            </a>
                          ) : (
                            'N/A'
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* MacaroniKID Events Table */}
          {events.filter(event => event.source === 'MacaroniKID').length > 0 && (
            <div className="events-table">
              <div className="table-header">
                <h2>MacaroniKID Events ({events.filter(event => event.source === 'MacaroniKID').length})</h2>
              </div>
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>Event</th>
                      <th>When</th>
                      <th>Who</th>
                      <th>Website</th>
                    </tr>
                  </thead>
                  <tbody>
                    {events.filter(event => event.source === 'MacaroniKID').map((event, index) => (
                      <tr key={`macaronikid-${index}`}>
                        <td className="event-title">
                          {event.title || 'Untitled Event'}
                        </td>
                        <td className="event-meta">{event.when || 'N/A'}</td>
                        <td className="event-meta">{event.description || 'Everyone'}</td>
                        <td>
                          {event.website ? (
                            <a
                              href={event.website}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="event-website"
                            >
                              Visit Website
                            </a>
                          ) : (
                            'N/A'
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Schools Events Table */}
          {events.filter(event => event.source && event.source.includes('Schools')).length > 0 && (
            <div className="events-table">
              <div className="table-header">
                <h2>School Events ({events.filter(event => event.source && event.source.includes('Schools')).length})</h2>
              </div>
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>Event</th>
                      <th>When</th>
                      <th>School</th>
                      <th>Website</th>
                    </tr>
                  </thead>
                  <tbody>
                    {events.filter(event => event.source && event.source.includes('Schools')).map((event, index) => (
                      <tr key={`schools-${index}`}>
                        <td className="event-title">
                          {event.title || 'Untitled Event'}
                        </td>
                        <td className="event-meta">{event.when || 'N/A'}</td>
                        <td className="event-meta">{event.address || 'School Event'}</td>
                        <td>
                          {event.website ? (
                            <a
                              href={event.website}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="event-website"
                            >
                              Visit Calendar
                            </a>
                          ) : (
                            'N/A'
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Churches Events Table */}
          {events.filter(event => event.category === 'church' || (event.source && event.source.includes('church'))).length > 0 && (
            <div className="events-table">
              <div className="table-header">
                <h2>Church Events ({events.filter(event => event.category === 'church' || (event.source && event.source.includes('church'))).length})</h2>
              </div>
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>Event</th>
                      <th>When</th>
                      <th>Church</th>
                      <th>Description</th>
                      <th>Website</th>
                    </tr>
                  </thead>
                  <tbody>
                    {events.filter(event => event.category === 'church' || (event.source && event.source.includes('church'))).map((event, index) => (
                      <tr key={`churches-${index}`}>
                        <td className="event-title">
                          {event.title || 'Untitled Event'}
                        </td>
                        <td className="event-meta">{event.when || 'N/A'}</td>
                        <td className="event-meta">{event.source || 'Church Event'}</td>
                        <td className="event-description">
                          {event.description ? (
                            <span title={event.description}>
                              {event.description.length > 100 
                                ? `${event.description.substring(0, 100)}...` 
                                : event.description}
                            </span>
                          ) : (
                            'No description'
                          )}
                        </td>
                        <td>
                          {event.website ? (
                            <a
                              href={event.website}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="event-website"
                            >
                              Learn More
                            </a>
                          ) : (
                            'N/A'
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {!loading && events.length === 0 && success && (
        <div className="no-events">
          <h3>No family events found for the selected criteria.</h3>
          <p>Try refreshing or contact support if the issue persists.</p>
        </div>
      )}
    </div>
  );
}

export default App;
