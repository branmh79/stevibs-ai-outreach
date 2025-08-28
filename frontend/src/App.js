import React, { useState } from 'react';
import axios from 'axios';
import { format } from 'date-fns';

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
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
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
      
      if (startDate) {
        params.start_date = startDate;
      }
      if (endDate) {
        params.end_date = endDate;
      }

      const response = await axios.get('/api/events/family', { params });
      const data = response.data;

      if (data.error) {
        setError(data.error);
      } else if (data.success && data.events) {
        setEvents(data.events);
        setSuccess(`Found ${data.events.length} family events near ${location}`);
      } else {
        setError('No family events found.');
      }
    } catch (err) {
      setError(`Failed to fetch events: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    try {
      return format(new Date(dateString), 'MMM dd, yyyy');
    } catch {
      return dateString;
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

          <div className="form-group">
            <label htmlFor="startDate">Start Date (optional)</label>
            <input
              id="startDate"
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label htmlFor="endDate">End Date (optional)</label>
            <input
              id="endDate"
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
            />
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
        <div className="events-table">
          <div className="table-header">
            <h2>Family Events</h2>
          </div>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Event</th>
                  <th>Description</th>
                  <th>Contact</th>
                  <th>Website</th>
                </tr>
              </thead>
              <tbody>
                {events.map((event, index) => (
                  <tr key={index}>
                    <td className="event-title">
                      {event.title || 'Untitled Event'}
                    </td>
                    <td className="event-description" title={event.description}>
                      {event.description || 'N/A'}
                    </td>
                    <td className="event-contact">
                      <div>Email: {event.contact_email || 'N/A'}</div>
                      <div>Phone: {event.phone_number || 'N/A'}</div>
                    </td>
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
