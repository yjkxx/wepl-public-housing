document.addEventListener("DOMContentLoaded", () => {
  // Only run list functionality on index page
  if (!document.getElementById("housing-data")) {
    return;
  }

  const housingDataContainer = document.getElementById("housing-data")
  const housingCardsContainer = document.getElementById("housing-cards-container")
  const resultCountSpan = document.getElementById("result-count")
  const noResultsDiv = document.getElementById("no-results")
  const noResultsClearBtn = document.getElementById("no-results-clear-btn")

  const filterToggleBtn = document.getElementById("filter-toggle-btn")
  const filterCloseBtn = document.getElementById("filter-close-btn")
  const filterPanel = document.getElementById("filter-panel")
  const filterOverlay = document.getElementById("filter-overlay")
  const clearFiltersBtn = document.getElementById("clear-filters-btn")

  const supplyTypeIdSelect = document.getElementById("supply_type_id")
  const regionProvinceSelect = document.getElementById("region_province")
  const regionCitySelect = document.getElementById("region_city")
  const houseTypeSelect = document.getElementById("house_type")
  const incomeInput = document.getElementById("income")
  const assetInput = document.getElementById("asset")
  const vehicleInput = document.getElementById("vehicle")

  let allHousingData = []
  let currentFilters = {
    supply_type_id: "",
    region_province: "",
    region_city: "",
    house_type: "",
    income: "",
    asset: "",
    vehicle: "",
  }

  // Mappings
  const supplyTypeMapping = {
    1: "매입임대",
    2: "국민임대", 
    3: "안심주택",
    4: "장기전세",
    5: "행복주택",
    6: "신혼신생아 전세임대",
    7: "든든전세", // Add mapping for ID 7
    // Add more as needed
  }

  const agencyMapping = {
    1: "LH한국토지주택공사",
    2: "SH서울주택도시공사", 
    3: "부산도시공사",
    4: "인천도시공사",
    "HUG": "HUG 주택도시보증공사", // Add string mapping for HUG
    "LH": "LH한국토지주택공사",
    "SH": "SH서울주택도시공사",
    // Add more as needed
  }

  // Utility functions
  const getSupplyTypeColor = (typeId) => {
    switch (typeId) {
      case 1:
        return "bg-gray-100 text-gray-800 border-gray-300"
      case 2:
        return "bg-blue-100 text-blue-800 border-blue-300"
      case 3:
        return "bg-rose-100 text-rose-800 border-rose-300"
      case 4:
        return "bg-orange-100 text-orange-800 border-orange-300"
      case 5:
        return "bg-yellow-100 text-yellow-800 border-yellow-300"
      case 6:
        return "bg-pink-100 text-pink-800 border-pink-300"
      case 7:
        return "bg-amber-100 text-amber-800 border-amber-400"
      default:
        return "bg-gray-100 text-gray-800 border-gray-300"
    }
  }

  const getHouseTypeColor = (type) => {
    switch (type) {
      case "아파트":
        return "bg-sky-100 text-sky-800 border-sky-300"
      case "연립주택":
        return "bg-amber-100 text-amber-800 border-amber-300"
      case "다가구주택":
        return "bg-lime-100 text-lime-800 border-lime-300"
      case "단독주택":
        return "bg-stone-100 text-stone-800 border-stone-300"
      case "오피스텔(주거용)":
        return "bg-purple-100 text-purple-800 border-purple-300"
      case "다세대주택":
        return "bg-lime-100 text-lime-800 border-lime-300"
      default:
        return "bg-gray-100 text-gray-800 border-gray-300"
    }
  }

  const getStatusInfo = (applyStart, applyEnd) => {
    const today = new Date() // Use current date dynamically
    const startDate = new Date(applyStart)
    const endDate = new Date(applyEnd)
    
    if (today < startDate) {
      // Before application start - 공고중 (light green)
      return {
        status: "공고중",
        color: "bg-green-50 text-green-700 border-green-400"
      }
    } else if (today >= startDate && today <= endDate) {
      // Within application period - 접수중 (bright green)
      return {
        status: "접수중",
        color: "bg-green-200 text-green-900 border-green-800"
      }
    } else {
      // After application end - 종료 (red)
      return {
        status: "종료",
        color: "bg-red-100 text-red-800 border-red-300"
      }
    }
  }

  // Legacy function for backward compatibility - now uses getStatusInfo
  const getStatusColor = (status) => {
    return status === "Y"
      ? "bg-green-100 text-green-800 border-green-300"
      : "bg-red-100 text-red-800 border-red-300"
  }

  const formatDate = (dateString) => {
    return dateString.replace(/-/g, ".")
  }

  const formatCurrency = (amount) => {
    if (amount >= 100000000) {
      return `${(amount / 100000000).toFixed(1)}억원`
    } else if (amount >= 10000) {
      return `${(amount / 10000).toFixed(0)}만원`
    } else {
      return `${amount.toLocaleString()}원`
    }
  }

  // Data parsing from HTML
  function parseHousingDataFromHTML() {
    const items = housingDataContainer.querySelectorAll(".housing-item")
    const parsedData = []
    items.forEach((item) => {
      // Handle agency_id as either string or number
      let agencyId = item.dataset.agency_id;
      if (!isNaN(agencyId)) {
        agencyId = Number.parseInt(agencyId);
      }
      // Keep as string if it's not a number (like "HUG", "LH", "SH")

      parsedData.push({
        notice_id: Number.parseInt(item.dataset.notice_id),
        status: item.dataset.status,
        region_province: item.dataset.region_province,
        region_city: item.dataset.region_city,
        address_detail: item.dataset.address_detail,
        apply_start: item.dataset.apply_start,
        apply_end: item.dataset.apply_end,
        house_type: item.dataset.house_type,
        supply_type_id: Number.parseInt(item.dataset.supply_type_id),
        application_url: item.dataset.application_url,
        deposit: Number.parseFloat(item.dataset.deposit),
        monthly_rent: Number.parseFloat(item.dataset.monthly_rent),
        agency_id: agencyId, // Use the processed agency_id
        income_limit: Number.parseInt(item.dataset.income_limit),
        asset_limit: Number.parseInt(item.dataset.asset_limit),
        vehicle_limit: Number.parseInt(item.dataset.vehicle_limit),
      })
    })
    return parsedData
  }

  // Populate filter options
  function populateFilterOptions() {
    const uniqueProvinces = [...new Set(allHousingData.map((item) => item.region_province))]
    regionProvinceSelect.innerHTML =
      '<option value="">선택하세요</option>' + uniqueProvinces.map((p) => `<option value="${p}">${p}</option>`).join("")
    regionProvinceSelect.className += " filter-select"

    const uniqueHouseTypes = [...new Set(allHousingData.map((item) => item.house_type))]
    houseTypeSelect.innerHTML =
      '<option value="">선택하세요</option>' +
      uniqueHouseTypes.map((t) => `<option value="${t}">${t}</option>`).join("")
    houseTypeSelect.className += " filter-select"

    // Add classes to inputs
    incomeInput.className += " filter-input"
    assetInput.className += " filter-input"
    vehicleInput.className += " filter-input"
    supplyTypeIdSelect.className += " filter-select"
    regionCitySelect.className += " filter-select"

    updateCityOptions() // Initial population of cities
  }

  function updateCityOptions() {
    const selectedProvince = regionProvinceSelect.value
    const filteredCities = allHousingData.filter(
      (item) => !selectedProvince || item.region_province === selectedProvince,
    )
    const uniqueCities = [...new Set(filteredCities.map((item) => item.region_city))]
    regionCitySelect.innerHTML =
      '<option value="">선택하세요</option>' + uniqueCities.map((c) => `<option value="${c}">${c}</option>`).join("")
    regionCitySelect.className += " filter-select"
    // Reset city if the previously selected city is no longer in the list for the new province
    if (currentFilters.region_city && !uniqueCities.includes(currentFilters.region_city)) {
      currentFilters.region_city = ""
      regionCitySelect.value = ""
    }
  }

  // Render housing cards
  function renderHousingCards(data) {
    housingCardsContainer.innerHTML = ""
    if (data.length === 0) {
      noResultsDiv.classList.remove("hidden")
    } else {
      noResultsDiv.classList.add("hidden")
      data.forEach((housing) => {
        // Replace the cardHtml section in your renderHousingCards function with this:

// Replace the cardHtml section in your renderHousingCards function with this:

const cardHtml = `
<div class="housing-card bg-white rounded-lg shadow-sm hover:shadow-lg transition-all duration-200 relative cursor-pointer border border-gray-200" onclick="window.location.href='${housing.agency_id}-${housing.notice_id}.html'">
    <div class="p-6">
                        <div class="flex items-start justify-between mb-3">
                    <h3 class="text-xl font-semibold flex-1 pr-4">
                        ${housing.region_province} ${housing.region_city} ${housing.house_type}
                    </h3>
                    <div class="flex gap-2 flex-shrink-0">
                        <span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium border ${getStatusInfo(housing.apply_start, housing.apply_end).color}">
                            ${getStatusInfo(housing.apply_start, housing.apply_end).status}
                        </span>
                        <span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium border ${getSupplyTypeColor(housing.supply_type_id)}">
                            ${supplyTypeMapping[housing.supply_type_id]}
                        </span>
                        <span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium border ${getHouseTypeColor(housing.house_type)}">
                            ${housing.house_type}
                        </span>
                    </div>
                </div>

                <div class="flex items-center gap-4 text-sm text-gray-600 mb-3">
                    <div class="flex items-center gap-1">
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-map-pin w-4 h-4"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/></svg>
                        <span>${housing.region_province} ${housing.region_city}</span>
                    </div>
                    <div class="flex items-center gap-1">
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-calendar w-4 h-4"><rect width="18" height="18" x="3" y="4" rx="2" ry="2"/><line x1="16" x2="16" y1="2" y2="6"/><line x1="8" x2="8" y1="2" y2="6"/><line x1="3" x2="21" y1="10" y2="10"/></svg>
                        <span>${formatDate(housing.apply_start)} ~ ${formatDate(housing.apply_end)}</span>
                    </div>
                </div>

                <p class="text-gray-700 mb-3">${housing.address_detail}</p>
                <p class="text-sm text-gray-600 mb-3">
                    주관기관: ${agencyMapping[housing.agency_id]}
                </p>

                <div class="flex gap-4 text-sm mb-0">
                    <span>
                        보증금: <strong>${formatCurrency(housing.deposit)}</strong>
                    </span>
                    <span>
                        월세: <strong>${formatCurrency(housing.monthly_rent)}</strong>
                    </span>
                </div>

                <div class="flex justify-between items-end -mt-1">
                    <div class="flex gap-4 text-xs text-gray-500">
                        <span>소득한도: ${housing.income_limit.toLocaleString()}만원</span>
                        <span>자산한도: ${housing.asset_limit.toLocaleString()}만원</span>
                        <span>차량가액: ${housing.vehicle_limit.toLocaleString()}만원</span>
                    </div>
                    
                    <div class="flex gap-2 ml-4">
                        <button onclick="event.stopPropagation(); window.location.href='${housing.agency_id}-${housing.notice_id}.html'" class="details-button px-3 py-3 text-sm bg-gray-100 hover:bg-gray-200 border border-gray-300 rounded transition-colors min-w-[96px] font-semibold">
        상세보기
    </button>
    <button onclick="event.stopPropagation(); window.open('${housing.application_url}', '_blank')" class="apply-button px-5.5 py-3 text-sm bg-black hover:bg-gray-900 text-white rounded transition-colors flex flex-col items-center min-w-[140px] font-normal leading-tight">
        <span class="flex items-center gap-1 font-semibold leading-tight pl-2">
            <span>신청하기</span>
            <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-external-link"><path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/></svg>
        </span>
        <span class="block text-xs opacity-80 mt-0 leading-tight">${agencyMapping[housing.agency_id]}</span>
    </button>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
`
        housingCardsContainer.insertAdjacentHTML("beforeend", cardHtml)
      })
    }
    resultCountSpan.textContent = data.length
  }

  // Filter and render logic
  function applyFiltersAndRender() {
    const filtered = allHousingData.filter((item) => {
      const incomeMatch = !currentFilters.income || item.income_limit >= Number.parseInt(currentFilters.income)
      const assetMatch = !currentFilters.asset || item.asset_limit >= Number.parseInt(currentFilters.asset)
      const vehicleMatch = !currentFilters.vehicle || item.vehicle_limit >= Number.parseInt(currentFilters.vehicle)

      return (
        (!currentFilters.supply_type_id || item.supply_type_id === Number.parseInt(currentFilters.supply_type_id)) &&
        (!currentFilters.region_province || item.region_province === currentFilters.region_province) &&
        (!currentFilters.region_city || item.region_city === currentFilters.region_city) &&
        (!currentFilters.house_type || item.house_type === currentFilters.house_type) &&
        incomeMatch &&
        assetMatch &&
        vehicleMatch
      )
    })

    // Sort by status priority: 접수중 first, then 공고중, then 종료, then by notice_id descending
    filtered.sort((a, b) => {
      const statusA = getStatusInfo(a.apply_start, a.apply_end).status
      const statusB = getStatusInfo(b.apply_start, b.apply_end).status
      
      // Define priority order: 접수중 > 공고중 > 종료
      const statusPriority = { "접수중": 3, "공고중": 2, "종료": 1 }
      
      const priorityA = statusPriority[statusA] || 0
      const priorityB = statusPriority[statusB] || 0
      
      // First sort by status priority (higher priority first)
      if (priorityA !== priorityB) {
        return priorityB - priorityA
      }
      
      // Then sort by notice_id descending (newer first)
      return b.notice_id - a.notice_id
    })

    renderHousingCards(filtered)
  }

  function handleFilterChange(event) {
    currentFilters[event.target.id] = event.target.value
    if (event.target.id === "region_province") {
      updateCityOptions()
    }
    applyFiltersAndRender()
  }

  function clearAllFilters() {
    currentFilters = {
      supply_type_id: "",
      region_province: "",
      region_city: "",
      house_type: "",
      income: "",
      asset: "",
      vehicle: "",
    }
    supplyTypeIdSelect.value = ""
    regionProvinceSelect.value = ""
    regionCitySelect.value = ""
    houseTypeSelect.value = ""
    incomeInput.value = ""
    assetInput.value = ""
    vehicleInput.value = ""
    updateCityOptions() // Reset cities after clearing province
    applyFiltersAndRender()
  }

  // --- Filter State Persistence ---
  function saveFiltersToStorage() {
    const filterState = {
      supply_type_id: document.getElementById('supply_type_id').value,
      region_province: document.getElementById('region_province').value,
      region_city: document.getElementById('region_city').value,
      house_type: document.getElementById('house_type').value,
      income: document.getElementById('income').value,
      asset: document.getElementById('asset').value,
      vehicle: document.getElementById('vehicle').value
    };
    localStorage.setItem('housingFilters', JSON.stringify(filterState));
  }

  function loadFiltersFromStorage() {
    const saved = localStorage.getItem('housingFilters');
    if (!saved) return;
    try {
      const filterState = JSON.parse(saved);
      if (filterState.supply_type_id !== undefined) document.getElementById('supply_type_id').value = filterState.supply_type_id;
      if (filterState.region_province !== undefined) document.getElementById('region_province').value = filterState.region_province;
      if (filterState.region_city !== undefined) document.getElementById('region_city').value = filterState.region_city;
      if (filterState.house_type !== undefined) document.getElementById('house_type').value = filterState.house_type;
      if (filterState.income !== undefined) document.getElementById('income').value = filterState.income;
      if (filterState.asset !== undefined) document.getElementById('asset').value = filterState.asset;
      if (filterState.vehicle !== undefined) document.getElementById('vehicle').value = filterState.vehicle;
    } catch (e) {
      // ignore
    }
  }

  // Attach listeners to all filter fields
  ['supply_type_id','region_province','region_city','house_type','income','asset','vehicle'].forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener('change', saveFiltersToStorage);
      el.addEventListener('input', saveFiltersToStorage);
    }
  });

  // Load filters on page load
  window.addEventListener('DOMContentLoaded', loadFiltersFromStorage);

  // Event Listeners
  supplyTypeIdSelect.addEventListener("change", handleFilterChange)
  regionProvinceSelect.addEventListener("change", handleFilterChange)
  regionCitySelect.addEventListener("change", handleFilterChange)
  houseTypeSelect.addEventListener("change", handleFilterChange)
  incomeInput.addEventListener("input", handleFilterChange)
  assetInput.addEventListener("input", handleFilterChange)
  vehicleInput.addEventListener("input", handleFilterChange)

  clearFiltersBtn.addEventListener("click", clearAllFilters)
  noResultsClearBtn.addEventListener("click", clearAllFilters)

  filterToggleBtn.addEventListener("click", () => {
    filterPanel.classList.remove("hidden")
    filterPanel.classList.add("translate-x-0")
    filterOverlay.classList.remove("hidden")
  })

  filterCloseBtn.addEventListener("click", () => {
    filterPanel.classList.add("-translate-x-full")
    filterPanel.classList.add("hidden") // Hide after transition
    filterOverlay.classList.add("hidden")
  })

  filterOverlay.addEventListener("click", () => {
    filterPanel.classList.add("-translate-x-full")
    filterPanel.classList.add("hidden") // Hide after transition
    filterOverlay.classList.add("hidden")
  })

  // Initialize the page
  function initializePage() {
    allHousingData = parseHousingDataFromHTML()
    populateFilterOptions()
    applyFiltersAndRender()
  }

  initializePage()

  // Initialize Kakao Map with proper loading checks
  function initMap() {
    if (typeof kakao === 'undefined' || !kakao.maps) {
        console.log('Kakao Maps API not ready, retrying...');
        setTimeout(initMap, 100);
        return;
    }

    console.log('Kakao Maps API loaded successfully');

    var mapContainer = document.getElementById('map');
    if (!mapContainer) {
        console.error('Map container not found');
        return;
    }

    var mapOption = {
        center: new kakao.maps.LatLng(37.5172, 127.0473), // Gangnam-gu coordinates
        level: 3
    };

    try {
        var map = new kakao.maps.Map(mapContainer, mapOption);
        console.log('Map created successfully');

        // Create geocoder instance if services are available
        if (kakao.maps.services) {
            var geocoder = new kakao.maps.services.Geocoder();

            // Address to search for
            var address = '서울특별시 강남구 테헤란로 123';

            // Search for coordinates using address
            geocoder.addressSearch(address, function(result, status) {
                if (status === kakao.maps.services.Status.OK) {
                    var coords = new kakao.maps.LatLng(result[0].y, result[0].x);

                    // Create marker
                    var marker = new kakao.maps.Marker({
                        map: map,
                        position: coords
                    });

                    // Set map center to the location
                    map.setCenter(coords);

                    // Create info window
                    var infowindow = new kakao.maps.InfoWindow({
                        content: '<div style="width:200px;text-align:center;padding:6px 0;">서울특별시 강남구<br>아파트 위치</div>'
                    });
                    infowindow.open(map, marker);

                    console.log('Address geocoding successful');
                } else {
                    console.warn('Address search failed, using fallback coordinates');
                    // Create marker at fallback location
                    var marker = new kakao.maps.Marker({
                        map: map,
                        position: new kakao.maps.LatLng(37.5172, 127.0473)
                    });

                    var infowindow = new kakao.maps.InfoWindow({
                        content: '<div style="width:200px;text-align:center;padding:6px 0;">서울특별시 강남구<br>대략적 위치</div>'
                    });
                    infowindow.open(map, marker);
                }
            });
        } else {
            console.warn('Kakao Maps services not available, creating basic marker');
            // Create basic marker without geocoding
            var marker = new kakao.maps.Marker({
                map: map,
                position: new kakao.maps.LatLng(37.5172, 127.0473)
            });

            var infowindow = new kakao.maps.InfoWindow({
                content: '<div style="width:200px;text-align:center;padding:6px 0;">서울특별시 강남구<br>아파트 위치</div>'
            });
            infowindow.open(map, marker);
        }

    } catch (error) {
        console.error('Error creating map:', error);
        // Show error message in map container
        mapContainer.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;background:#f5f5f5;color:#666;text-align:center;"><div>지도를 불러올 수 없습니다.<br>잠시 후 다시 시도해주세요.</div></div>';
    }
  }
})

// Initialize map when page loads - works for both index and detail pages
window.onload = function() {
    console.log('Page loaded, initializing map...');
    
    // Check if we're on a detail page (has map container)
    if (document.getElementById('map')) {
        initDetailPageMap();
    }
};

// Map initialization function specifically for detail pages
function initDetailPageMap() {
    if (typeof kakao === 'undefined' || !kakao.maps) {
        console.log('Kakao Maps API not ready, retrying...');
        setTimeout(initDetailPageMap, 100);
        return;
    }
    
    console.log('Kakao Maps API loaded successfully');
    
    var mapContainer = document.getElementById('map');
    if (!mapContainer) {
        console.error('Map container not found');
        return;
    }

    var mapOption = {
        center: new kakao.maps.LatLng(37.5172, 127.0473), // Default Gangnam-gu coordinates
        level: 7 // Changed from 3 to 7 for more zoomed out view
    };

    try {
        var map = new kakao.maps.Map(mapContainer, mapOption);
        console.log('Map created successfully');
        
        // Create geocoder instance if services are available
        if (kakao.maps.services) {
            var geocoder = new kakao.maps.services.Geocoder();
            
            // Try to get address from the page content
            var addressElements = document.querySelectorAll('[data-address], .address-detail');
            var address = '서울특별시 강남구 테헤란로 123'; // Default address
            
            // Try to extract address from page content
            var addressSpans = document.querySelectorAll('span');
            for (var i = 0; i < addressSpans.length; i++) {
                var text = addressSpans[i].textContent;
                if (text && (text.includes('시') || text.includes('구') || text.includes('동'))) {
                    if (text.length > 5 && text.length < 50) {
                        address = text;
                        break;
                    }
                }
            }
            
            console.log('Using address for geocoding:', address);
            
            // Search for coordinates using address
            geocoder.addressSearch(address, function(result, status) {
                if (status === kakao.maps.services.Status.OK) {
                    var coords = new kakao.maps.LatLng(result[0].y, result[0].x);
                    
                    // Create marker
                    var marker = new kakao.maps.Marker({
                        map: map,
                        position: coords
                    });
                    
                    // Set map center to the location
                    map.setCenter(coords);
                    
                    // Create info window with location name
                    var locationName = address.split(' ').slice(0, 3).join(' '); // Get first 3 parts
                    var infowindow = new kakao.maps.InfoWindow({
                        content: '<div style="width:200px;text-align:center;padding:6px 0;">' + locationName + '<br>임대주택 위치</div>'
                    });
                    infowindow.open(map, marker);
                    
                    console.log('Address geocoding successful');
                } else {
                    console.warn('Address search failed, using fallback coordinates');
                    // Create marker at fallback location
                    var marker = new kakao.maps.Marker({
                        map: map,
                        position: new kakao.maps.LatLng(37.5172, 127.0473)
                    });
                    
                    var infowindow = new kakao.maps.InfoWindow({
                        content: '<div style="width:200px;text-align:center;padding:6px 0;">대략적 위치<br>임대주택</div>'
                    });
                    infowindow.open(map, marker);
                }
            });
        } else {
            console.warn('Kakao Maps services not available, creating basic marker');
            // Create basic marker without geocoding
            var marker = new kakao.maps.Marker({
                map: map,
                position: new kakao.maps.LatLng(37.5172, 127.0473)
            });
            
            var infowindow = new kakao.maps.InfoWindow({
                content: '<div style="width:200px;text-align:center;padding:6px 0;">임대주택 위치<br>지도 서비스 제한</div>'
            });
            infowindow.open(map, marker);
        }
        
    } catch (error) {
        console.error('Error creating map:', error);
        // Show error message in map container
        mapContainer.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;background:#f5f5f5;color:#666;text-align:center;"><div>지도를 불러올 수 없습니다.<br>잠시 후 다시 시도해주세요.</div></div>';
    }
}
