import { useEffect, useState, useCallback, useRef } from 'react'

type OnboardingData = {
  full_name?: string
  age?: number
  sex?: string
  height?: number
  weight?: number
  location?: string
  blood_type?: string
  allergies?: string
  medications?: string
  conditions?: string
  symptoms_current?: string
  exercise_frequency?: string
  sleep_hours?: number
  stress_level?: string
  blood_pressure?: string
  heart_rate?: number
}

type OverviewPageProps = {
  onboardingData: OnboardingData | null
  healthSummary?: string
  onAddDocuments: () => void
  onViewRecords: () => void
  onOpenChat: () => void
  accessToken: string | null
  apiUrl: string | undefined
}

type Appointment = {
  id: number
  hospital_name: string
  hospital_address: string
  status: 'pending' | 'calling' | 'confirmed' | 'failed' | 'cancelled'
  appointment_date: string | null
  appointment_time: string | null
  doctor_name: string
  department: string
  purpose: string
  notes: string
  created_at: string
}

type Hospital = {
  place_id: string
  name: string
  vicinity: string
  rating?: number
  user_ratings_total?: number
  geometry: {
    location: {
      lat: number
      lng: number
    }
  }
  opening_hours?: {
    open_now?: boolean
  }
  types?: string[]
}

type UserLocation = {
  lat: number
  lng: number
}

declare global {
  interface Window {
    google: typeof google
    initMap: () => void
  }
}

export function OverviewPage({ onboardingData, healthSummary, onAddDocuments, onViewRecords, onOpenChat, accessToken, apiUrl }: OverviewPageProps) {
  const [hospitals, setHospitals] = useState<Hospital[]>([])
  const [userLocation, setUserLocation] = useState<UserLocation | null>(null)
  const [mapLoaded, setMapLoaded] = useState(false)
  const [loadingHospitals, setLoadingHospitals] = useState(false)
  const [locationError, setLocationError] = useState<string | null>(null)
  const [selectedHospital, setSelectedHospital] = useState<Hospital | null>(null)
  const mapRef = useRef<HTMLDivElement>(null)
  const mapInstanceRef = useRef<google.maps.Map | null>(null)
  const markersRef = useRef<google.maps.Marker[]>([])
  
  // Appointment states
  const [appointments, setAppointments] = useState<Appointment[]>([])
  const [bookingHospital, setBookingHospital] = useState<Hospital | null>(null)
  const [bookingPurpose, setBookingPurpose] = useState('')
  const [isBooking, setIsBooking] = useState(false)
  const [bookingResult, setBookingResult] = useState<{success: boolean; message: string; appointment?: Appointment} | null>(null)

  const computeBMI = (height?: number, weight?: number): string | null => {
    if (!height || !weight) return null
    const heightM = height / 100
    return (weight / (heightM * heightM)).toFixed(1)
  }

  const bmi = computeBMI(onboardingData?.height, onboardingData?.weight)

  const getHealthStatus = (): { status: string; color: string } => {
    if (onboardingData?.symptoms_current) {
      return { status: 'Needs Attention', color: 'attention' }
    }
    if (onboardingData?.conditions) {
      return { status: 'Under Care', color: 'watch' }
    }
    return { status: 'Stable', color: 'good' }
  }

  const healthStatus = getHealthStatus()

  const loadGoogleMapsScript = useCallback(() => {
    const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY
    if (!apiKey) {
      setLocationError('Google Maps API key not configured')
      return
    }

    if (window.google?.maps) {
      setMapLoaded(true)
      return
    }

    const script = document.createElement('script')
    script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&libraries=places`
    script.async = true
    script.defer = true
    script.onload = () => setMapLoaded(true)
    script.onerror = () => setLocationError('Failed to load Google Maps')
    document.head.appendChild(script)
  }, [])

  const getUserLocation = useCallback(() => {
    if (!navigator.geolocation) {
      setLocationError('Geolocation not supported')
      return
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setUserLocation({
          lat: position.coords.latitude,
          lng: position.coords.longitude
        })
        setLocationError(null)
      },
      (error) => {
        console.error('Geolocation error:', error)
        // Default to a location based on onboarding data or fallback
        const defaultLoc = { lat: 28.6139, lng: 77.2090 } // Delhi as fallback
        setUserLocation(defaultLoc)
        setLocationError('Using default location. Enable location for accurate results.')
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 300000 }
    )
  }, [])

  const searchNearbyHospitals = useCallback(() => {
    if (!mapLoaded || !userLocation || !mapInstanceRef.current) return

    setLoadingHospitals(true)
    const service = new google.maps.places.PlacesService(mapInstanceRef.current)

    const request: google.maps.places.PlaceSearchRequest = {
      location: new google.maps.LatLng(userLocation.lat, userLocation.lng),
      radius: 5000,
      type: 'hospital'
    }

    service.nearbySearch(request, (results, status) => {
      setLoadingHospitals(false)
      if (status === google.maps.places.PlacesServiceStatus.OK && results) {
        const hospitalResults = results.slice(0, 10).map(place => ({
          place_id: place.place_id || '',
          name: place.name || 'Unknown Hospital',
          vicinity: place.vicinity || 'Address not available',
          rating: place.rating,
          user_ratings_total: place.user_ratings_total,
          geometry: {
            location: {
              lat: place.geometry?.location?.lat() || 0,
              lng: place.geometry?.location?.lng() || 0
            }
          },
          opening_hours: place.opening_hours,
          types: place.types
        }))
        setHospitals(hospitalResults)
        addMarkersToMap(hospitalResults)
      }
    })
  }, [mapLoaded, userLocation])

  const initializeMap = useCallback(() => {
    if (!mapRef.current || !userLocation || !mapLoaded) return

    const map = new google.maps.Map(mapRef.current, {
      center: { lat: userLocation.lat, lng: userLocation.lng },
      zoom: 14,
      styles: [
        { featureType: 'poi.medical', stylers: [{ visibility: 'on' }] },
        { featureType: 'poi.business', stylers: [{ visibility: 'off' }] }
      ],
      mapTypeControl: false,
      streetViewControl: false,
      fullscreenControl: true
    })

    // Add user location marker
    new google.maps.Marker({
      position: { lat: userLocation.lat, lng: userLocation.lng },
      map,
      title: 'Your Location',
      icon: {
        path: google.maps.SymbolPath.CIRCLE,
        scale: 10,
        fillColor: '#4285F4',
        fillOpacity: 1,
        strokeColor: '#ffffff',
        strokeWeight: 2
      }
    })

    mapInstanceRef.current = map
  }, [userLocation, mapLoaded])

  const addMarkersToMap = (hospitalList: Hospital[]) => {
    if (!mapInstanceRef.current) return

    // Clear existing markers
    markersRef.current.forEach(marker => marker.setMap(null))
    markersRef.current = []

    hospitalList.forEach((hospital, index) => {
      const marker = new google.maps.Marker({
        position: { lat: hospital.geometry.location.lat, lng: hospital.geometry.location.lng },
        map: mapInstanceRef.current!,
        title: hospital.name,
        label: {
          text: String(index + 1),
          color: '#ffffff',
          fontSize: '12px',
          fontWeight: 'bold'
        },
        icon: {
          path: google.maps.SymbolPath.CIRCLE,
          scale: 15,
          fillColor: '#E53935',
          fillOpacity: 1,
          strokeColor: '#ffffff',
          strokeWeight: 2
        }
      })

      marker.addListener('click', () => {
        setSelectedHospital(hospital)
      })

      markersRef.current.push(marker)
    })
  }

  const openDirections = (hospital: Hospital) => {
    if (!userLocation) return
    const url = `https://www.google.com/maps/dir/?api=1&origin=${userLocation.lat},${userLocation.lng}&destination=${hospital.geometry.location.lat},${hospital.geometry.location.lng}&travelmode=driving`
    window.open(url, '_blank')
  }

  useEffect(() => {
    loadGoogleMapsScript()
    getUserLocation()
  }, [loadGoogleMapsScript, getUserLocation])

  useEffect(() => {
    if (mapLoaded && userLocation) {
      initializeMap()
    }
  }, [mapLoaded, userLocation, initializeMap])

  useEffect(() => {
    if (mapInstanceRef.current && userLocation) {
      searchNearbyHospitals()
    }
  }, [mapInstanceRef.current, userLocation, searchNearbyHospitals])

  // Fetch appointments on mount
  const fetchAppointments = useCallback(async () => {
    if (!apiUrl || !accessToken) return
    try {
      const res = await fetch(`${apiUrl}/api/appointments/`, {
        headers: { Authorization: `Bearer ${accessToken}` }
      })
      if (res.ok) {
        const data = await res.json()
        setAppointments(data.appointments || [])
      }
    } catch (e) {
      console.error('Failed to fetch appointments:', e)
    }
  }, [apiUrl, accessToken])

  useEffect(() => {
    fetchAppointments()
  }, [fetchAppointments])

  // Book appointment
  const bookAppointment = async (hospital: Hospital) => {
    if (!apiUrl || !accessToken) return
    
    setIsBooking(true)
    setBookingResult(null)
    
    try {
      const res = await fetch(`${apiUrl}/api/appointments/`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${accessToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          hospital_name: hospital.name,
          hospital_address: hospital.vicinity,
          hospital_place_id: hospital.place_id,
          purpose: bookingPurpose || onboardingData?.symptoms_current || 'General consultation'
        })
      })
      
      const data = await res.json()
      
      if (res.ok && data.success) {
        setBookingResult({
          success: true,
          message: data.appointment.status === 'confirmed' 
            ? `Appointment confirmed for ${data.appointment.appointment_date} at ${data.appointment.appointment_time}`
            : 'Appointment request processed',
          appointment: data.appointment
        })
        fetchAppointments()
      } else {
        setBookingResult({
          success: false,
          message: data.detail || 'Failed to book appointment'
        })
      }
    } catch (e) {
      setBookingResult({
        success: false,
        message: 'Network error. Please try again.'
      })
    } finally {
      setIsBooking(false)
    }
  }

  const closeBookingModal = () => {
    setBookingHospital(null)
    setBookingPurpose('')
    setBookingResult(null)
  }

  const formatDateTime = (date: string | null, time: string | null) => {
    if (!date) return 'Pending'
    const dateObj = new Date(date)
    const dateStr = dateObj.toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short' })
    if (time) {
      return `${dateStr} at ${time}`
    }
    return dateStr
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'confirmed': return 'status-confirmed'
      case 'pending': 
      case 'calling': return 'status-pending'
      case 'failed': 
      case 'cancelled': return 'status-failed'
      default: return ''
    }
  }

  const stats = [
    { label: 'Health Status', value: healthStatus.status, icon: '❤️', color: healthStatus.color },
    { label: 'BMI', value: bmi || '—', icon: '⚖️', color: 'neutral' },
    { label: 'Age', value: onboardingData?.age ? `${onboardingData.age} yrs` : '—', icon: '🎂', color: 'neutral' },
    { label: 'Blood Type', value: onboardingData?.blood_type || '—', icon: '🩸', color: 'neutral' }
  ]

  return (
    <div className="overview-page">
      {/* Welcome Section */}
      <div className="overview-welcome">
        <div className="welcome-content">
          <h1 className="welcome-title">
            Welcome back, {onboardingData?.full_name?.split(' ')[0] || 'there'}!
          </h1>
          <p className="welcome-subtitle">
            Your personalized health dashboard with nearby hospitals and medical facilities.
          </p>
        </div>
        <div className="welcome-actions">
          <button className="overview-btn primary" onClick={onAddDocuments}>
            <span className="btn-icon">📄</span>
            Add Documents
          </button>
          <button className="overview-btn secondary" onClick={onViewRecords}>
            <span className="btn-icon">📋</span>
            View Records
          </button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="overview-stats-grid">
        {stats.map((stat) => (
          <div key={stat.label} className={`overview-stat-card stat-${stat.color}`}>
            <span className="stat-icon">{stat.icon}</span>
            <div className="stat-info">
              <p className="stat-value">{stat.value}</p>
              <p className="stat-label">{stat.label}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Main Content Grid */}
      <div className="overview-main-grid">
        {/* Map Section */}
        <div className="overview-map-section">
          <div className="section-header">
            <div>
              <h2 className="section-title">🏥 Nearby Hospitals</h2>
              <p className="section-subtitle">
                {hospitals.length > 0 
                  ? `${hospitals.length} hospitals within 5km radius`
                  : 'Finding hospitals near you...'}
              </p>
            </div>
            {locationError && (
              <span className="location-warning">⚠️ {locationError}</span>
            )}
          </div>

          <div className="map-container">
            {!mapLoaded ? (
              <div className="map-loading">
                <div className="loading-spinner"></div>
                <p>Loading map...</p>
              </div>
            ) : (
              <div ref={mapRef} className="google-map"></div>
            )}
          </div>

          {/* Hospital List */}
          <div className="hospital-list">
            {loadingHospitals ? (
              <div className="loading-hospitals">
                <div className="loading-spinner small"></div>
                <span>Finding hospitals...</span>
              </div>
            ) : hospitals.length > 0 ? (
              hospitals.map((hospital, index) => (
                <div 
                  key={hospital.place_id} 
                  className={`hospital-card ${selectedHospital?.place_id === hospital.place_id ? 'selected' : ''}`}
                  onClick={() => setSelectedHospital(hospital)}
                >
                  <div className="hospital-number">{index + 1}</div>
                  <div className="hospital-info">
                    <h4 className="hospital-name">{hospital.name}</h4>
                    <p className="hospital-address">{hospital.vicinity}</p>
                    <div className="hospital-meta">
                      {hospital.rating && (
                        <span className="hospital-rating">
                          ⭐ {hospital.rating.toFixed(1)}
                          {hospital.user_ratings_total && (
                            <span className="rating-count">({hospital.user_ratings_total})</span>
                          )}
                        </span>
                      )}
                      {hospital.opening_hours && (
                        <span className={`hospital-status ${hospital.opening_hours.open_now ? 'open' : 'closed'}`}>
                          {hospital.opening_hours.open_now ? '● Open' : '● Closed'}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="hospital-actions">
                    <button 
                      className="directions-btn"
                      onClick={(e) => {
                        e.stopPropagation()
                        openDirections(hospital)
                      }}
                      title="Get directions"
                    >
                      🧭
                    </button>
                    <button
                      className="book-appointment-btn"
                      onClick={(e) => {
                        e.stopPropagation()
                        setBookingHospital(hospital)
                      }}
                      title="Book Appointment"
                    >
                      📅 Book
                    </button>
                  </div>
                </div>
              ))
            ) : (
              <div className="no-hospitals">
                <p>No hospitals found nearby. Try enabling location services.</p>
              </div>
            )}
          </div>
        </div>

        {/* Right Sidebar */}
        <div className="overview-sidebar">
          {/* Health Summary Card */}
          <div className="sidebar-card health-summary-card">
            <div className="card-header">
              <h3>📊 Health Summary</h3>
            </div>
            <div className="card-content">
              {healthSummary ? (
                <p className="health-summary-text">{healthSummary}</p>
              ) : (
                <p className="no-summary">
                  Upload your medical documents to get an AI-generated health summary.
                </p>
              )}
            </div>
          </div>

          {/* Quick Info Card */}
          <div className="sidebar-card quick-info-card">
            <div className="card-header">
              <h3>📋 Quick Info</h3>
            </div>
            <div className="card-content">
              <div className="info-row">
                <span className="info-label">Full Name</span>
                <span className="info-value">{onboardingData?.full_name || 'Not set'}</span>
              </div>
              <div className="info-row">
                <span className="info-label">Age / Sex</span>
                <span className="info-value">
                  {onboardingData?.age ? `${onboardingData.age} yrs` : '—'} 
                  {onboardingData?.sex && ` / ${onboardingData.sex}`}
                </span>
              </div>
              <div className="info-row">
                <span className="info-label">Height / Weight</span>
                <span className="info-value">
                  {onboardingData?.height ? `${onboardingData.height} cm` : '—'} 
                  {onboardingData?.weight && ` / ${onboardingData.weight} kg`}
                </span>
              </div>
              <div className="info-row">
                <span className="info-label">Location</span>
                <span className="info-value">{onboardingData?.location || 'Not set'}</span>
              </div>
              <div className="info-row">
                <span className="info-label">Blood Pressure</span>
                <span className="info-value">{onboardingData?.blood_pressure || 'Not measured'}</span>
              </div>
              <div className="info-row">
                <span className="info-label">Heart Rate</span>
                <span className="info-value">{onboardingData?.heart_rate ? `${onboardingData.heart_rate} bpm` : 'Not measured'}</span>
              </div>
            </div>
          </div>

          {/* Medical Info Card */}
          <div className="sidebar-card medical-info-card">
            <div className="card-header">
              <h3>💊 Medical Info</h3>
            </div>
            <div className="card-content">
              <div className="info-row">
                <span className="info-label">Allergies</span>
                <span className="info-value">{onboardingData?.allergies || 'None recorded'}</span>
              </div>
              <div className="info-row">
                <span className="info-label">Medications</span>
                <span className="info-value">{onboardingData?.medications || 'None recorded'}</span>
              </div>
              <div className="info-row">
                <span className="info-label">Conditions</span>
                <span className="info-value">{onboardingData?.conditions || 'None recorded'}</span>
              </div>
            </div>
          </div>

          {/* Lifestyle Card */}
          <div className="sidebar-card lifestyle-card">
            <div className="card-header">
              <h3>🏃 Lifestyle</h3>
            </div>
            <div className="card-content">
              <div className="info-row">
                <span className="info-label">Exercise</span>
                <span className="info-value">{onboardingData?.exercise_frequency || 'Not tracked'}</span>
              </div>
              <div className="info-row">
                <span className="info-label">Sleep</span>
                <span className="info-value">{onboardingData?.sleep_hours ? `${onboardingData.sleep_hours} hrs/day` : 'Not tracked'}</span>
              </div>
              <div className="info-row">
                <span className="info-label">Stress Level</span>
                <span className="info-value">{onboardingData?.stress_level || 'Not assessed'}</span>
              </div>
            </div>
          </div>

          {/* AI Chat Card */}
          <div className="sidebar-card chat-promo-card">
            <div className="card-header">
              <h3>🤖 AI Health Assistant</h3>
            </div>
            <div className="card-content">
              <p className="chat-promo-text">
                Get instant answers about your health, medications, symptoms, and more from our AI assistant.
              </p>
              <button className="chat-btn" onClick={onOpenChat}>
                Start Chat →
              </button>
            </div>
          </div>

          {/* Current Symptoms */}
          {onboardingData?.symptoms_current && (
            <div className="sidebar-card symptoms-card">
              <div className="card-header">
                <h3>🩺 Current Symptoms</h3>
              </div>
              <div className="card-content">
                <p className="symptoms-text">{onboardingData.symptoms_current}</p>
              </div>
            </div>
          )}

          {/* Appointments Card */}
          {appointments.length > 0 && (
            <div className="sidebar-card appointments-card">
              <div className="card-header">
                <h3>📅 Your Appointments</h3>
              </div>
              <div className="card-content">
                {appointments.slice(0, 3).map((apt) => (
                  <div key={apt.id} className={`appointment-item ${getStatusColor(apt.status)}`}>
                    <div className="appointment-header">
                      <span className="appointment-hospital">{apt.hospital_name}</span>
                      <span className={`appointment-status ${apt.status}`}>{apt.status}</span>
                    </div>
                    {apt.status === 'confirmed' && (
                      <div className="appointment-details">
                        <p className="appointment-datetime">
                          📆 {formatDateTime(apt.appointment_date, apt.appointment_time)}
                        </p>
                        {apt.doctor_name && (
                          <p className="appointment-doctor">👨‍⚕️ {apt.doctor_name}</p>
                        )}
                        {apt.department && (
                          <p className="appointment-dept">🏥 {apt.department}</p>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Booking Modal */}
      {bookingHospital && (
        <div className="booking-modal-overlay" onClick={closeBookingModal}>
          <div className="booking-modal" onClick={(e) => e.stopPropagation()}>
            <div className="booking-modal-header">
              <h2>📞 Book Appointment</h2>
              <button className="modal-close-btn" onClick={closeBookingModal}>×</button>
            </div>
            
            <div className="booking-modal-content">
              <div className="booking-hospital-info">
                <h3>{bookingHospital.name}</h3>
                <p>{bookingHospital.vicinity}</p>
                {bookingHospital.rating && (
                  <span className="hospital-rating">⭐ {bookingHospital.rating.toFixed(1)}</span>
                )}
              </div>

              {!bookingResult && !isBooking && (
                <>
                  <div className="booking-form">
                    <label htmlFor="purpose">Reason for Visit</label>
                    <textarea
                      id="purpose"
                      value={bookingPurpose}
                      onChange={(e) => setBookingPurpose(e.target.value)}
                      placeholder={onboardingData?.symptoms_current || "Describe your symptoms or reason for visit..."}
                      rows={3}
                    />
                  </div>

                  <div className="booking-info-box">
                    <p>🤖 Our AI will call the hospital and book an appointment for you.</p>
                    <p>This usually takes 1-2 minutes.</p>
                  </div>

                  <button 
                    className="booking-confirm-btn"
                    onClick={() => bookAppointment(bookingHospital)}
                  >
                    📞 Call & Book Appointment
                  </button>
                </>
              )}

              {isBooking && (
                <div className="booking-progress">
                  <div className="loading-spinner"></div>
                  <p className="booking-status">Calling hospital...</p>
                  <p className="booking-substatus">Our AI is speaking with the hospital to book your appointment</p>
                </div>
              )}

              {bookingResult && (
                <div className={`booking-result ${bookingResult.success ? 'success' : 'error'}`}>
                  <div className="result-icon">{bookingResult.success ? '✅' : '❌'}</div>
                  <h3>{bookingResult.success ? 'Appointment Booked!' : 'Booking Failed'}</h3>
                  <p>{bookingResult.message}</p>
                  
                  {bookingResult.success && bookingResult.appointment && (
                    <div className="result-details">
                      {bookingResult.appointment.appointment_date && (
                        <p><strong>Date:</strong> {bookingResult.appointment.appointment_date}</p>
                      )}
                      {bookingResult.appointment.appointment_time && (
                        <p><strong>Time:</strong> {bookingResult.appointment.appointment_time}</p>
                      )}
                      {bookingResult.appointment.doctor_name && (
                        <p><strong>Doctor:</strong> {bookingResult.appointment.doctor_name}</p>
                      )}
                      {bookingResult.appointment.department && (
                        <p><strong>Department:</strong> {bookingResult.appointment.department}</p>
                      )}
                    </div>
                  )}
                  
                  <button className="booking-done-btn" onClick={closeBookingModal}>
                    {bookingResult.success ? 'Done' : 'Close'}
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
