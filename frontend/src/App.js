import React, { useState } from 'react';
import axios from 'axios';

// Location data (same as backend)
const LOCATION_ADDRESSES = {
  "Covington, GA": "3104 Highway 278 NW, Covington, GA 30014",
  "Douglasville, GA": "7003 N. Concourse Parkway, Douglasville, GA 30134",
  "Duluth, GA": "1500 Pleasant Hill Rd, Duluth, GA 30096",
  "Gainesville, GA": "1500 Browns Bridge Rd., Gainesville, GA 30501",
  "Hiram, GA": "4215 Jimmy Lee Smith Pkwy, Hiram, GA 30141",
  "Fayetteville, GA": "107 Banks Station, Fayetteville, GA 30214",
  "Snellville, GA": "1977 Scenic Hwy S, Snellville, GA 30078",
  "Stockbridge, GA": "3570 GA-138, Stockbridge, GA 30281",
  "Warner Robins, GA": "2907 Watson Blvd, Warner Robins, GA 31093",
  "Findlay, OH": "7535 Patriot Dr., Findlay, OH 45840"
};

const LOCATION_OPTIONS = Object.keys(LOCATION_ADDRESSES);

function App() {
  const [location, setLocation] = useState(LOCATION_OPTIONS[0]);
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleSearch = async () => {
    setLoading(true);
    setError('');
    setSuccess('');
    setEvents([]);

    try {
      const params = {
        location: location
      };
      
      const response = await axios.get('/api/events/family', { params });
      const data = response.data;

      if (data.error) {
        setError(data.error);
      } else if (data.success && data.events) {
        setEvents(data.events);
        const facebookCount = data.events.filter(e => e.source && e.source.includes('Facebook')).length;
        const macaroniCount = data.events.filter(e => e.source === 'MacaroniKID').length;
        const schoolsCount = data.events.filter(e => e.source && e.source.includes('Schools')).length;
        const churchesCount = data.events.filter(e => e.category === 'church' || (e.source && e.source.includes('church'))).length;
        let successMsg = `Found ${data.events.length} family events near ${location}`;
        
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
      setError(`Failed to fetch events: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container">
      <div className="header">
        <h1>SteviB's AI Outreach</h1>
      </div>

      <div className="controls">
        <div className="form-row">
          <div className="form-group">
            <label htmlFor="location">Location</label>
            <select
              id="location"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
            >
              {LOCATION_OPTIONS.map(option => (
                <option key={option} value={option}>{option}</option>
              ))}
            </select>
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
          <p>Try adjusting your location or date range.</p>
        </div>
      )}
    </div>
  );
}

export default App;
