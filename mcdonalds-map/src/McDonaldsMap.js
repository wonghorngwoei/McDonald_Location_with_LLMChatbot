import React, { useEffect, useState, useRef } from "react";
import { GoogleMap, LoadScript, Marker, Circle, InfoWindow } from "@react-google-maps/api";

const API_BASE_URL = process.env.REACT_APP_API_URL || "https://mindhive-assessment-wonghorngwoei.onrender.com";

const GOOGLE_API_KEY = process.env.REACT_APP_GOOGLE_MAPS_API_KEY;
const mapContainerStyle = { width: "100%", height: "600px" };
const center = { lat: 3.139, lng: 101.6869 };
const RADIUS = 5000;

const McDonaldsMap = () => {
  const messagesEndRef = useRef(null);
  const [stores, setStores] = useState([]);
  const [selectedLocation, setSelectedLocation] = useState(null);
  const [intersectedStores, setIntersectedStores] = useState(new Set());
  const [chatVisible, setChatVisible] = useState(false);
  const [chatMessages, setChatMessages] = useState([]);
  const [query, setQuery] = useState("");

  // Fetch store data on component mount
  useEffect(() => {
    fetch(`${API_BASE_URL}/stores`)
      .then(response => response.json())
      .then(data => {
        if (data.stores) {
          setStores(data.stores);
          findIntersections(data.stores);
        }
      })
      .catch(error => console.error("Error fetching data:", error));
  }, []);

  // Auto-scroll chat to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  // Calculate distance between stores
  const haversineDistance = (lat1, lon1, lat2, lon2) => {
    const R = 6371000;
    const toRad = angle => (Math.PI / 180) * angle;
    const dLat = toRad(lat2 - lat1);
    const dLon = toRad(lon2 - lon1);
    const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
              Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) *
              Math.sin(dLon / 2) * Math.sin(dLon / 2);
    return R * (2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a)));
  };

  // Find stores with overlapping coverage areas
  const findIntersections = (stores) => {
    const intersected = new Set();
    stores.forEach((storeA, indexA) => {
      stores.forEach((storeB, indexB) => {
        if (indexA !== indexB) {
          const distance = haversineDistance(
            parseFloat(storeA.latitude), parseFloat(storeA.longitude),
            parseFloat(storeB.latitude), parseFloat(storeB.longitude)
          );
          if (distance <= RADIUS * 2) {
            intersected.add(storeA.name);
            intersected.add(storeB.name);
          }
        }
      });
    });
    setIntersectedStores(intersected);
  };

  // Handle marker click on map
  const handleMarkerClick = (store) => {
    if (selectedLocation && selectedLocation.lat === parseFloat(store.latitude) && 
        selectedLocation.lng === parseFloat(store.longitude)) {
      setSelectedLocation(null);
    } else {
      setSelectedLocation({ 
        ...store, 
        lat: parseFloat(store.latitude), 
        lng: parseFloat(store.longitude) 
      });
    }
  };

  // Handle sending chat messages
  const handleSendMessage = async () => {
    if (!query.trim()) return;
    
    // Add user message to chat
    const userMessage = {
      sender: "user",
      content: query,
      timestamp: new Date().toLocaleTimeString()
    };
    setChatMessages(prev => [...prev, userMessage]);
    setQuery("");

    const queryLower = query.toLowerCase().trim();
    
    // Skip greeting/thanks checks for location/feature queries
    const isLocationQuery = queryLower.includes("outlet") || 
                          queryLower.includes("store") || 
                          queryLower.includes("location") ||
                          queryLower.includes("find") ||
                          queryLower.includes("list") ||
                          queryLower.includes("which");

    if (!isLocationQuery) {
      // Handle thank you messages
      if (['thank you', 'thanks', 'appreciate it'].some(phrase => queryLower.includes(phrase))) {
        const thankYouResponse = {
          sender: "bot",
          timestamp: new Date().toLocaleTimeString(),
          content: "You're welcome! Happy to help out! Have a great day!"
        };
        setChatMessages(prev => [...prev, thankYouResponse]);
        return;
      }

      // Handle greetings
      if (['hi', 'hello', 'hey'].some(phrase => queryLower.includes(phrase))) {
        const greetingResponse = {
          sender: "bot",
          timestamp: new Date().toLocaleTimeString(),
          content: "Hello! 👋 What are you looking for?"
        };
        setChatMessages(prev => [...prev, greetingResponse]);
        return;
      }
    }

    try {
      // Send query to backend
      const response = await fetch(
        `${API_BASE_URL}/chatbot/?query=${encodeURIComponent(query)}`
      );
      
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      
      const data = await response.json();
      
      // Format bot response
      const botResponse = {
        sender: "bot",
        timestamp: new Date().toLocaleTimeString(),
        content: formatBotResponse(data)
      };
      
      setChatMessages(prev => [...prev, botResponse]);
    } catch (error) {
      console.error("Error fetching chatbot response:", error);
      const errorMessage = {
        sender: "bot",
        timestamp: new Date().toLocaleTimeString(),
        content: (
          <div style={{ color: "#d32f2f", display: "flex", alignItems: "center", gap: "8px" }}>
            ❌ Sorry, I encountered an error. Please try again later.
          </div>
        )
      };
      setChatMessages(prev => [...prev, errorMessage]);
    }
  };

  // Render feature icons for store cards
  const renderFeatureIcons = (features) => {
    const activeFeatures = Object.entries(features)
      .filter(([_, value]) => value)
      .map(([key]) => key);

    if (activeFeatures.length === 0) return null;

    return (
      <div style={{ 
        display: "flex", 
        flexWrap: "wrap", 
        gap: "6px", 
        marginTop: "8px",
        alignItems: "center"
      }}>
        <span style={{ fontSize: "12px", color: "#666" }}>Features:</span>
        {activeFeatures.map((feature, index) => (
          <span 
            key={index}
            style={{
              backgroundColor: "#ffcc00",
              color: "#333",
              padding: "2px 6px",
              borderRadius: "10px",
              fontSize: "11px",
              display: "flex",
              alignItems: "center",
              gap: "2px"
            }}
          >
            {getFeatureIcon(feature)} {formatFeatureName(feature)}
          </span>
        ))}
      </div>
    );
  };

  // Get icon for each feature
  const getFeatureIcon = (feature) => {
    const icons = {
      "24_hours": "⏰",
      "birthday_party": "🎉",
      "breakfast": "🍳",
      "cashless": "💳",
      "dessert_center": "🍰",
      "digital_kiosk": "🖥️",
      "mccafe": "☕",
      "wifi": "📶",
      "mcdelivery": "🛵"
    };
    return icons[feature] || "✨";
  };

  // Format feature names for display
  const formatFeatureName = (feature) => {
    const names = {
      "24_hours": "24H",
      "birthday_party": "Party",
      "breakfast": "Breakfast",
      "cashless": "Cashless",
      "dessert_center": "Dessert",
      "digital_kiosk": "Kiosk",
      "mccafe": "McCafé",
      "wifi": "WiFi",
      "mcdelivery": "Delivery"
    };
    return names[feature] || feature;
  };

  // Format bot response with store data
  const formatBotResponse = (data) => {
    if (!data.data || data.data.length === 0) {
      return (
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          🔍 No McDonald's stores found matching your query.
        </div>
      );
    }

    // Customize response header based on query type
    let responseHeader;
    if (data.response.includes("24-hour")) {
      responseHeader = `🍟 ${data.response}`;
    } else if (data.response.includes("birthday parties")) {
      responseHeader = `🎉 ${data.response}`;
    } else {
      responseHeader = `🍔 ${data.response}`;
    }

    return (
      <div>
        <div style={{ 
          display: "flex", 
          alignItems: "center", 
          gap: "8px",
          marginBottom: "12px",
          color: "#d50000",
          fontWeight: "bold"
        }}>
          {responseHeader}
        </div>
        
        <div style={{ 
          maxHeight: "200px", 
          overflowY: "auto",
          paddingRight: "8px",
          display: "flex",
          flexDirection: "column",
          gap: "10px"
        }}>
          {data.data.map((store, index) => (
            <div key={index} style={{
              backgroundColor: "#f9f9f9",
              borderRadius: "8px",
              padding: "12px",
              borderLeft: "4px solid #ffcc00"
            }}>
              <div style={{ fontWeight: "600", marginBottom: "6px" }}>
                {store.name}
              </div>
              
              <div style={{ display: "flex", gap: "6px", marginBottom: "4px" }}>
                📍 {store.address}
              </div>
              
              {store.operating_hours && (
                <div style={{ display: "flex", gap: "6px", marginBottom: "4px" }}>
                  ⏰ {store.operating_hours}
                </div>
              )}
              
              {store.contact?.telephone && (
                <div style={{ display: "flex", gap: "6px", marginBottom: "4px" }}>
                  📞 {store.contact.telephone}
                </div>
              )}
              
              {store.features && renderFeatureIcons(store.features)}
              
              {store.waze_link && (
                <a 
                  href={store.waze_link} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "4px",
                    color: "#1a73e8",
                    textDecoration: "none",
                    marginTop: "6px"
                  }}
                >
                  🗺️ Open in Waze
                </a>
              )}
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <LoadScript googleMapsApiKey={GOOGLE_API_KEY}>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
        {/* Store count display */}
        <div style={{ 
          width: "100%", 
          padding: "10px", 
          backgroundColor: "#f8f8f8", 
          textAlign: "center",
          fontSize: "18px",
          fontWeight: "bold",
          marginBottom: "10px"
        }}>
          Total McDonald's Stores Found around Kuala Lumpur: {stores.length}
        </div>
        
        {/* Google Map */}
        <GoogleMap mapContainerStyle={mapContainerStyle} zoom={12} center={center}>
          {stores.map((store, index) => {
            const isIntersected = intersectedStores.has(store.name);
            return (
              <React.Fragment key={index}>
                <Marker 
                  position={{ lat: parseFloat(store.latitude), lng: parseFloat(store.longitude) }}
                  onClick={() => handleMarkerClick(store)} 
                  icon={{
                    url: "https://maps.google.com/mapfiles/ms/icons/restaurant.png",
                    scaledSize: new window.google.maps.Size(32, 32)
                  }}
                />
                
                {selectedLocation && selectedLocation.lat === parseFloat(store.latitude) && 
                 selectedLocation.lng === parseFloat(store.longitude) && (
                  <InfoWindow
                    position={{ lat: parseFloat(store.latitude), lng: parseFloat(store.longitude) }}
                    onCloseClick={() => setSelectedLocation(null)}
                  >
                    <div style={{ padding: "8px", maxWidth: "200px" }}>
                      <h3 style={{ margin: "4px 0", color: "#d50000" }}>{store.name}</h3>
                      <p style={{ margin: "4px 0" }}>{store.address}</p>
                      {store.operating_hours && (
                        <p style={{ margin: "4px 0" }}><strong>Hours:</strong> {store.operating_hours}</p>
                      )}
                      {store.contact?.telephone && (
                        <p style={{ margin: "4px 0" }}><strong>Phone:</strong> {store.contact.telephone}</p>
                      )}
                      {store.features && (
                        <div style={{ marginTop: "6px" }}>
                          <strong>Features:</strong>
                          <div style={{ display: "flex", flexWrap: "wrap", gap: "4px", marginTop: "4px" }}>
                            {Object.entries(store.features)
                              .filter(([_, value]) => value)
                              .map(([feature, _], i) => (
                                <span key={i} style={{
                                  backgroundColor: "#ffcc00",
                                  padding: "2px 6px",
                                  borderRadius: "10px",
                                  fontSize: "10px"
                                }}>
                                  {getFeatureIcon(feature)} {formatFeatureName(feature)}
                                </span>
                              ))}
                          </div>
                        </div>
                      )}
                      {store.waze_link && (
                        <a 
                          href={store.waze_link} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          style={{
                            display: "inline-block",
                            marginTop: "8px",
                            color: "#1a73e8",
                            textDecoration: "none"
                          }}
                        >
                          View in Waze →
                        </a>
                      )}
                    </div>
                  </InfoWindow>
                )}
                
                <Circle 
                  center={{ lat: parseFloat(store.latitude), lng: parseFloat(store.longitude) }}
                  radius={RADIUS}
                  options={{
                    strokeColor: isIntersected ? "#FF5252" : "#4285F4",
                    fillColor: isIntersected ? "#FF5252" : "#4285F4",
                    strokeOpacity: 0.8,
                    strokeWeight: 2,
                    fillOpacity: 0.2
                  }}
                />
              </React.Fragment>
            );
          })}
        </GoogleMap>
        
        {/* Chatbot UI */}
        <div style={{ width: "600px", marginTop: "10px", textAlign: "center" }}>
          <button 
            onClick={() => setChatVisible(!chatVisible)}
            style={{
              backgroundColor: "#ffcc00",
              border: "none",
              borderRadius: "10px",
              padding: "10px 20px",
              fontSize: "16px",
              cursor: "pointer",
              marginBottom: "10px",
              display: "flex",
              alignItems: "center",
              gap: "8px",
              marginLeft: "auto",
              marginRight: "auto"
            }}
          >
            {chatVisible ? "Close Chat" : (
              <>
                <span style={{ fontSize: "20px" }}>💬</span>
                McBot the McDonald's Chatbot
              </>
            )}
          </button>
          
          {chatVisible && (
            <div style={{
              width: "100%",
              height: "300px",
              backgroundColor: "white",
              borderRadius: "10px",
              boxShadow: "0 4px 8px rgba(0,0,0,0.2)",
              padding: "15px",
              display: "flex",
              flexDirection: "column"
            }}>
              {/* Messages container */}
              <div style={{ 
                flex: 1,
                overflowY: "auto",
                marginBottom: "10px",
                paddingRight: "8px",
                background: "#fafafa",
                borderRadius: "8px",
                padding: "10px"
              }}>
                {chatMessages.map((msg, index) => (
                  <div key={index} style={{
                    marginBottom: "12px",
                    textAlign: msg.sender === "user" ? "right" : "left"
                  }}>
                    {/* Message header */}
                    <div style={{
                      fontSize: "11px",
                      color: "#999",
                      marginBottom: "4px",
                      textAlign: msg.sender === "user" ? "right" : "left"
                    }}>
                      {msg.sender === "user" ? "You" : "McBot"} • {msg.timestamp}
                    </div>
                    
                    {/* Message content */}
                    <div style={{
                      display: "inline-block",
                      padding: "10px 14px",
                      borderRadius: "14px",
                      backgroundColor: msg.sender === "user" ? "#ffcc00" : "#f1f1f1",
                      maxWidth: "80%",
                      textAlign: "left",
                      wordBreak: "break-word"
                    }}>
                      {msg.content}
                    </div>
                  </div>
                ))}
                <div ref={messagesEndRef} />
              </div>
              
              {/* Input area */}
              <div style={{ display: "flex" }}>
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                  placeholder="Ask about locations, features (WiFi, McCafe, etc)..."
                  style={{
                    flexGrow: 1,
                    padding: "8px 12px",
                    borderRadius: "20px",
                    border: "1px solid #ddd",
                    minWidth: 0,
                    outline: "none",
                    fontSize: "14px"
                  }}
                />
                <button
                  onClick={handleSendMessage}
                  disabled={!query.trim()}
                  style={{
                    marginLeft: "5px",
                    backgroundColor: query.trim() ? "#ffcc00" : "#ccc",
                    border: "none",
                    padding: "8px 15px",
                    borderRadius: "20px",
                    cursor: query.trim() ? "pointer" : "default",
                    color: query.trim() ? "#333" : "#666"
                  }}
                >
                  Send
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </LoadScript>
  );
};

export default McDonaldsMap;