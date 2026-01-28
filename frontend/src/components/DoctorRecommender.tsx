import { useState, useEffect, useCallback, useRef } from 'react'

type Specialty = {
  specialty: string
  search_term: string
  reason: string
  urgency: 'low' | 'medium' | 'high'
  priority: number
}

type Place = {
  place_id: string
  name: string
  address: string
  rating: number | null
  user_ratings_total: number
  lat: number
  lng: number
  open_now: boolean | null
  phone?: string
}

type RecommendationsData = {
  specialties: Specialty[]
  location: { lat: number; lng: number } | null
  places: Record<string, Place[]>
}

type Props = {
  accessToken: string | null
  apiUrl: string | undefined
  userLocation: string | undefined
}

// Track if Google Maps script is already loading/loaded
let googleMapsPromise: Promise<void> | null = null

function loadGoogleMaps(apiKey: string): Promise<void> {
  if (window.google?.maps?.places) {
    return Promise.resolve()
  }

  if (googleMapsPromise) {
    return googleMapsPromise
  }

  googleMapsPromise = new Promise((resolve, reject) => {
    const callbackName = `gmapsCallback_${Date.now()}`
    
    ;(window as unknown as Record<string, () => void>)[callbackName] = () => {
      delete (window as unknown as Record<string, unknown>)[callbackName]
      resolve()
    }

    const script = document.createElement('script')
    script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&libraries=places&callback=${callbackName}&loading=async`
    script.async = true
    script.onerror = () => {
      googleMapsPromise = null
      reject(new Error('Failed to load Google Maps'))
    }
    document.head.appendChild(script)
  })

  return googleMapsPromise
}

export function DoctorRecommender({ accessToken, apiUrl, userLocation }: Props) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<RecommendationsData | null>(null)
  const [selectedSpecialty, setSelectedSpecialty] = useState<string | null>(null)
  const [selectedPlace, setSelectedPlace] = useState<Place | null>(null)
  const [searchLocation, setSearchLocation] = useState(userLocation || '')
  const [mapLoaded, setMapLoaded] = useState(false)
  const [nearbyPlaces, setNearbyPlaces] = useState<Place[]>([])
  const [searchingNearby, setSearchingNearby] = useState(false)
  
  const mapRef = useRef<HTMLDivElement>(null)
  const mapInstanceRef = useRef<google.maps.Map | null>(null)
  const markersRef = useRef<google.maps.Marker[]>([])
  const infoWindowsRef = useRef<google.maps.InfoWindow[]>([])
  const placesServiceRef = useRef<google.maps.places.PlacesService | null>(null)
  const geocoderRef = useRef<google.maps.Geocoder | null>(null)
  const userMarkerRef = useRef<google.maps.Marker | null>(null)

  const googleMapsKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY as string

  // Fetch AI recommendations from backend
  const fetchRecommendations = useCallback(async (lat?: number, lng?: number) => {
    if (!apiUrl || !accessToken) return

    setLoading(true)
    setError(null)

    try {
      let url = `${apiUrl}/api/recommendations/`
      if (lat && lng) {
        url += `?lat=${lat}&lng=${lng}`
      }

      const res = await fetch(url, {
        headers: { Authorization: `Bearer ${accessToken}` }
      })

      if (!res.ok) {
        const body = await res.json()
        throw new Error(body.detail || `HTTP ${res.status}`)
      }

      const result = await res.json()
      setData(result)

      if (result.specialties?.length > 0) {
        setSelectedSpecialty(result.specialties[0].specialty)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load recommendations')
    } finally {
      setLoading(false)
    }
  }, [apiUrl, accessToken])

  // Load Google Maps script
  useEffect(() => {
    if (!googleMapsKey) {
      setError('Google Maps API key not configured.')
      return
    }

    loadGoogleMaps(googleMapsKey)
      .then(() => setMapLoaded(true))
      .catch((err) => setError(err.message))
  }, [googleMapsKey])

  // Initialize map once Google Maps is loaded
  useEffect(() => {
    if (!mapLoaded || !mapRef.current || mapInstanceRef.current) return

    const defaultCenter = { lat: 20.5937, lng: 78.9629 }

    const map = new google.maps.Map(mapRef.current, {
      zoom: 5,
      center: defaultCenter,
      mapTypeControl: false,
      streetViewControl: false,
      fullscreenControl: true,
      zoomControl: true,
      styles: [
        { featureType: 'poi.business', stylers: [{ visibility: 'off' }] },
        { featureType: 'poi.park', elementType: 'labels', stylers: [{ visibility: 'off' }] }
      ]
    })

    mapInstanceRef.current = map
    placesServiceRef.current = new google.maps.places.PlacesService(map)
    geocoderRef.current = new google.maps.Geocoder()

    // Try to get user's current location
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const userLoc = {
            lat: position.coords.latitude,
            lng: position.coords.longitude
          }
          
          map.setCenter(userLoc)
          map.setZoom(13)
          addUserMarker(userLoc, map)
          fetchRecommendations(userLoc.lat, userLoc.lng)
        },
        () => fetchRecommendations()
      )
    } else {
      fetchRecommendations()
    }
  }, [mapLoaded, fetchRecommendations])

  // Add user location marker
  const addUserMarker = (location: google.maps.LatLngLiteral, map: google.maps.Map) => {
    if (userMarkerRef.current) {
      userMarkerRef.current.setPosition(location)
      return
    }

    userMarkerRef.current = new google.maps.Marker({
      position: location,
      map,
      title: 'Your Location',
      icon: {
        path: google.maps.SymbolPath.CIRCLE,
        scale: 14,
        fillColor: '#dc2626',
        fillOpacity: 1,
        strokeColor: '#ffffff',
        strokeWeight: 4
      },
      zIndex: 1000
    })

    const infoWindow = new google.maps.InfoWindow({
      content: `<div style="padding:10px;text-align:center;"><strong style="color:#dc2626;">📍 You are here</strong></div>`
    })

    userMarkerRef.current.addListener('click', () => {
      infoWindow.open(map, userMarkerRef.current!)
    })
  }

  // Clear all markers
  const clearMarkers = useCallback(() => {
    markersRef.current.forEach(m => m.setMap(null))
    markersRef.current = []
    infoWindowsRef.current.forEach(iw => iw.close())
    infoWindowsRef.current = []
  }, [])

  // Search nearby using Google Places
  const searchNearbyAtLocation = useCallback((location: google.maps.LatLng | google.maps.LatLngLiteral, searchTerm: string) => {
    if (!placesServiceRef.current || !mapInstanceRef.current) return

    setSearchingNearby(true)
    clearMarkers()

    const request: google.maps.places.PlaceSearchRequest = {
      location,
      radius: 5000,
      keyword: searchTerm,
      type: 'doctor' as unknown as string
    }

    placesServiceRef.current.nearbySearch(request, (results, status) => {
      if (status === google.maps.places.PlacesServiceStatus.OK && results) {
        const openPlaces = results
          .filter(p => !p.opening_hours || p.opening_hours.open_now)
          .slice(0, 10)

        const places: Place[] = openPlaces.map(place => ({
          place_id: place.place_id || '',
          name: place.name || '',
          address: place.vicinity || '',
          rating: place.rating || null,
          user_ratings_total: place.user_ratings_total || 0,
          lat: place.geometry?.location?.lat() || 0,
          lng: place.geometry?.location?.lng() || 0,
          open_now: place.opening_hours?.open_now ?? null
        }))

        setNearbyPlaces(places)
        addMarkersToMap(places)
      } else {
        setNearbyPlaces([])
      }
      setSearchingNearby(false)
    })
  }, [clearMarkers])

  // Add markers to map
  const addMarkersToMap = useCallback((places: Place[]) => {
    if (!mapInstanceRef.current) return

    clearMarkers()
    const bounds = new google.maps.LatLngBounds()

    if (userMarkerRef.current?.getPosition()) {
      bounds.extend(userMarkerRef.current.getPosition()!)
    }

    places.forEach((place, index) => {
      const position = { lat: place.lat, lng: place.lng }
      
      const marker = new google.maps.Marker({
        position,
        map: mapInstanceRef.current!,
        title: place.name,
        label: {
          text: String(index + 1),
          color: 'white',
          fontWeight: 'bold',
          fontSize: '12px'
        },
        icon: {
          path: google.maps.SymbolPath.CIRCLE,
          scale: 16,
          fillColor: '#3b82f6',
          fillOpacity: 1,
          strokeColor: '#ffffff',
          strokeWeight: 2
        }
      })

      const infoContent = `
        <div style="min-width:220px;padding:12px;font-family:system-ui,sans-serif;">
          <h6 style="margin:0 0 6px;color:#0f172a;font-weight:600;font-size:14px;">${place.name}</h6>
          ${place.rating ? `<p style="margin:0 0 4px;font-size:12px;color:#475569;">⭐ ${place.rating} (${place.user_ratings_total})</p>` : ''}
          <p style="margin:0 0 8px;font-size:12px;color:#64748b;">${place.address}</p>
          <a href="https://www.google.com/maps/dir/?api=1&destination=${place.lat},${place.lng}&destination_place_id=${place.place_id}" 
             target="_blank" 
             style="display:inline-block;padding:8px 16px;background:#0f172a;color:white;text-decoration:none;border-radius:6px;font-size:12px;font-weight:500;">
            Get Directions
          </a>
        </div>
      `

      const infoWindow = new google.maps.InfoWindow({ content: infoContent })

      marker.addListener('click', () => {
        infoWindowsRef.current.forEach(iw => iw.close())
        infoWindow.open(mapInstanceRef.current!, marker)
        setSelectedPlace(place)
      })

      markersRef.current.push(marker)
      infoWindowsRef.current.push(infoWindow)
      bounds.extend(position)
    })

    if (places.length > 0) {
      mapInstanceRef.current.fitBounds(bounds, 60)
    }
  }, [clearMarkers])

  // Use current location
  const useMyLocation = () => {
    if (!navigator.geolocation) {
      alert('Geolocation not supported.')
      return
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const userLoc = { lat: position.coords.latitude, lng: position.coords.longitude }

        if (mapInstanceRef.current) {
          mapInstanceRef.current.setCenter(userLoc)
          mapInstanceRef.current.setZoom(13)
          addUserMarker(userLoc, mapInstanceRef.current)

          if (selectedSpecialty && data) {
            const spec = data.specialties.find(s => s.specialty === selectedSpecialty)
            if (spec) searchNearbyAtLocation(userLoc, spec.search_term)
          }
        }
      },
      () => alert('Unable to get location.')
    )
  }

  // Search by entered location
  const searchByLocation = () => {
    if (!searchLocation.trim() || !geocoderRef.current) return

    geocoderRef.current.geocode({ address: searchLocation }, (results, status) => {
      if (status === 'OK' && results?.[0]) {
        const location = results[0].geometry.location
        
        if (mapInstanceRef.current) {
          mapInstanceRef.current.setCenter(location)
          mapInstanceRef.current.setZoom(13)
          addUserMarker({ lat: location.lat(), lng: location.lng() }, mapInstanceRef.current)

          if (selectedSpecialty && data) {
            const spec = data.specialties.find(s => s.specialty === selectedSpecialty)
            if (spec) searchNearbyAtLocation(location, spec.search_term)
          }
        }
      } else {
        alert('Location not found.')
      }
    })
  }

  // When specialty changes, search again
  useEffect(() => {
    if (!selectedSpecialty || !data || !mapInstanceRef.current) return

    const spec = data.specialties.find(s => s.specialty === selectedSpecialty)
    if (!spec) return

    const center = mapInstanceRef.current.getCenter()
    if (center) searchNearbyAtLocation(center, spec.search_term)
  }, [selectedSpecialty, data, searchNearbyAtLocation])

  // Click on place card
  const handlePlaceClick = (place: Place, index: number) => {
    setSelectedPlace(place)
    
    if (mapInstanceRef.current && markersRef.current[index]) {
      mapInstanceRef.current.panTo({ lat: place.lat, lng: place.lng })
      mapInstanceRef.current.setZoom(15)
      
      infoWindowsRef.current.forEach(iw => iw.close())
      infoWindowsRef.current[index]?.open(mapInstanceRef.current, markersRef.current[index])
    }
  }

  const getUrgencyColor = (urgency: string) => {
    switch (urgency) {
      case 'high': return '#dc2626'
      case 'medium': return '#f59e0b'
      default: return '#22c55e'
    }
  }

  if (loading && !data) {
    return (
      <div className="dr-loading">
        <div className="loading-spinner" />
        <p>Finding doctors near you...</p>
      </div>
    )
  }

  return (
    <div className="dr-container">
      {/* Left: Results Panel */}
      <div className="dr-panel">
        <div className="dr-panel-header">
          <h2>Find Doctors Near You</h2>
          <p>AI-recommended specialists based on your health profile</p>
        </div>

        {error && <div className="dr-error">{error}</div>}

        {/* Specialty Pills */}
        {data?.specialties && data.specialties.length > 0 && (
          <div className="dr-specialties">
            {data.specialties.map((spec) => (
              <button
                key={spec.specialty}
                className={`dr-specialty-pill ${selectedSpecialty === spec.specialty ? 'active' : ''}`}
                onClick={() => setSelectedSpecialty(spec.specialty)}
              >
                <span className="dr-urgency-dot" style={{ backgroundColor: getUrgencyColor(spec.urgency) }} />
                {spec.specialty}
              </button>
            ))}
          </div>
        )}

        {/* Reason */}
        {selectedSpecialty && data?.specialties && (
          <div className="dr-reason">
            <strong>Why:</strong> {data.specialties.find(s => s.specialty === selectedSpecialty)?.reason}
          </div>
        )}

        {/* Results */}
        <div className="dr-results">
          <h3>
            {searchingNearby ? 'Searching...' : `Nearby ${selectedSpecialty || 'Doctors'}`}
            {!searchingNearby && nearbyPlaces.length > 0 && <span className="dr-count">({nearbyPlaces.length})</span>}
          </h3>

          {searchingNearby && (
            <div className="dr-results-loading"><div className="loading-spinner" /></div>
          )}

          {!searchingNearby && nearbyPlaces.length === 0 && (
            <div className="dr-empty">
              <p>No results found nearby.</p>
              <p>Try a different location or specialty.</p>
            </div>
          )}

          <div className="dr-places">
            {nearbyPlaces.map((place, index) => (
              <div
                key={place.place_id}
                className={`dr-place ${selectedPlace?.place_id === place.place_id ? 'selected' : ''}`}
                onClick={() => handlePlaceClick(place, index)}
              >
                <div className="dr-place-num">{index + 1}</div>
                <div className="dr-place-info">
                  <h4>{place.name}</h4>
                  <p className="dr-place-addr">{place.address}</p>
                  <div className="dr-place-meta">
                    {place.rating && <span>⭐ {place.rating}</span>}
                    {place.open_now !== null && (
                      <span className={place.open_now ? 'open' : 'closed'}>
                        {place.open_now ? 'Open' : 'Closed'}
                      </span>
                    )}
                  </div>
                </div>
                <a
                  href={`https://www.google.com/maps/dir/?api=1&destination=${place.lat},${place.lng}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="dr-place-dir"
                  onClick={(e) => e.stopPropagation()}
                >
                  →
                </a>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right: Map */}
      <div className="dr-map-section">
        <div ref={mapRef} className="dr-map" />
        {!mapLoaded && (
          <div className="dr-map-placeholder">
            <div className="loading-spinner" />
            <p>Loading map...</p>
          </div>
        )}
        
        {/* Search bar overlay on map */}
        <div className="dr-search-overlay">
          <input
            type="text"
            className="dr-search-input"
            placeholder="Search location..."
            value={searchLocation}
            onChange={(e) => setSearchLocation(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && searchByLocation()}
          />
          <button className="dr-search-btn" onClick={searchByLocation}>Search</button>
          <button className="dr-location-btn" onClick={useMyLocation} title="Use my location">📍</button>
        </div>

        {/* Legend */}
        <div className="dr-legend">
          <span className="dr-legend-item"><span className="dr-legend-dot red"></span> Your location</span>
          <span className="dr-legend-item"><span className="dr-legend-dot blue"></span> Doctors/Hospitals</span>
        </div>
      </div>
    </div>
  )
}
