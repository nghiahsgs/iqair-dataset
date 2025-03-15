from playwright.sync_api import sync_playwright
import json
from datetime import datetime
import csv
import os
import pathlib
from zoneinfo import ZoneInfo
from typing import Dict, List, Optional
import re

# Define cities data
CITIES = [
    {
        "name": "hanoi",
        "display_name": "Hà Nội",
        "url": "https://www.iqair.com/vi/vietnam/hanoi/hanoi"
    },
    {
        "name": "ho-chi-minh-city",
        "display_name": "Hồ Chí Minh",
        "url": "https://www.iqair.com/vi/vietnam/ho-chi-minh-city/ho-chi-minh-city"
    },
    {
        "name": "da-nang",
        "display_name": "Đà Nẵng",
        "url": "https://www.iqair.com/vi/vietnam/da-nang/da-nang"
    },
    {
        "name": "hai-phong",
        "display_name": "Hải Phòng",
        "url": "https://www.iqair.com/vi/vietnam/thanh-pho-hai-phong/haiphong"
    },
    {
        "name": "nha-trang",
        "display_name": "Nha Trang",
        "url": "https://www.iqair.com/vi/vietnam/khanh-hoa/nha-trang"
    },
    {
        "name": "can-tho",
        "display_name": "Cần Thơ",
        "url": "https://www.iqair.com/vi/vietnam/thanh-pho-can-tho/can-tho"
    },
    {
        "name": "hue",
        "display_name": "Huế",
        "url": "https://www.iqair.com/vietnam/tinh-thua-thien-hue/hue"
    },
    {
        "name": "vinh",
        "display_name": "Vinh",
        "url": "https://www.iqair.com/vi/vietnam/tinh-nghe-an/vinh"
    }
]

def get_vietnam_time():
    """Get current time in Vietnam timezone (GMT+7)"""
    return datetime.now(ZoneInfo("Asia/Bangkok"))  # Bangkok uses GMT+7 like Vietnam

def validate_aqi(aqi: str) -> Optional[str]:
    """Validate AQI value"""
    try:
        # Remove any non-digit characters and convert to int
        aqi_value = int(re.sub(r'\D', '', aqi))
        if 0 <= aqi_value <= 500:  # Valid AQI range
            return str(aqi_value)
    except (ValueError, TypeError):
        pass
    return None

def validate_weather_icon(icon: str) -> Optional[str]:
    """Validate weather icon URL"""
    if icon and isinstance(icon, str) and icon.startswith('/dl/web/weather/'):
        return icon
    return None

def validate_wind_speed(speed: str) -> Optional[str]:
    """Validate wind speed"""
    try:
        # Check if matches pattern like "10.2 km/h" or "8.5 mph"
        if re.match(r'^\d+(\.\d+)?\s*(km/h|mph)$', speed.strip()):
            # Convert mph to km/h if needed
            speed = speed.strip()
            if 'mph' in speed:
                # Extract numeric value
                value = float(re.match(r'^\d+(\.\d+)?', speed).group())
                # Convert to km/h (1 mile = 1.60934 kilometers)
                km_value = value * 1.60934
                return f"{km_value:.1f} km/h"
            return speed
    except (ValueError, TypeError, AttributeError):
        pass
    return None

def validate_humidity(humidity: str) -> Optional[str]:
    """Validate humidity"""
    try:
        # Check if matches pattern like "39%"
        if re.match(r'^\d{1,3}%$', humidity.strip()):
            return humidity.strip()
    except (ValueError, TypeError, AttributeError):
        pass
    return None

def crawl_city_data(page, city: Dict) -> Optional[Dict]:
    """Crawl data for a specific city"""
    print(f"\nAccessing {city['display_name']} ({city['url']})...")
    
    try:
        # Navigate to city page
        page.goto(city['url'])
        
        # Wait for content to load
        page.wait_for_selector(".aqi-value__estimated")
        
        # Extract and validate data
        aqi_raw = page.query_selector(".aqi-value__estimated").text_content()
        weather_icon_raw = page.query_selector(".air-quality-forecast-container-weather__icon").get_attribute("src")
        wind_speed_raw = page.query_selector(".air-quality-forecast-container-wind__label").text_content()
        humidity_raw = page.query_selector(".air-quality-forecast-container-humidity__label").text_content()
        
        # Validate all fields
        aqi = validate_aqi(aqi_raw)
        weather_icon = validate_weather_icon(weather_icon_raw)
        wind_speed = validate_wind_speed(wind_speed_raw)
        humidity = validate_humidity(humidity_raw)
        
        # If any validation fails, return None
        if not all([aqi, weather_icon, wind_speed, humidity]):
            print(f"Invalid data found for {city['display_name']}:")
            if not aqi: print(f"  - Invalid AQI: {aqi_raw}")
            if not weather_icon: print(f"  - Invalid weather icon: {weather_icon_raw}")
            if not wind_speed: print(f"  - Invalid wind speed: {wind_speed_raw}")
            if not humidity: print(f"  - Invalid humidity: {humidity_raw}")
            return None
        
        # Create data dictionary with Vietnam time
        current_time = get_vietnam_time()
        data = {
            "timestamp": current_time.isoformat(),
            "city": city['display_name'],
            "aqi": aqi,
            "weather_icon": weather_icon,
            "wind_speed": wind_speed,
            "humidity": humidity
        }
        
        return data
        
    except Exception as e:
        print(f"Error extracting data for {city['display_name']}: {str(e)}")
        return None

def save_to_csv(data: Dict, city_name: str):
    """Save data to CSV file for a specific city"""
    now = get_vietnam_time()
    result_dir = pathlib.Path(f"result/{city_name}")
    result_dir.mkdir(parents=True, exist_ok=True)
    
    # Create filename based on current month
    filename = f"aqi_{city_name}_{now.year}_{now.strftime('%b').lower()}.csv"
    filepath = result_dir / filename
    
    # Define CSV headers
    headers = ["timestamp", "city", "aqi", "weather_icon", "wind_speed", "humidity"]
    
    # Check if file exists to determine if we need to write headers
    file_exists = filepath.exists()
    
    with open(filepath, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        
        # Write headers if file is new
        if not file_exists:
            writer.writeheader()
        
        # Write data
        writer.writerow(data)
    
    return filepath

def crawl_all_cities():
    """Crawl data for all cities"""
    results = []
    for city in CITIES:
        print(f"\n{'='*50}")
        print(f"Processing {city['display_name']}...")
        try:
            with sync_playwright() as p:
                try:
                    # Launch new browser for each city
                    browser = p.chromium.launch(headless=True)
                    page = browser.new_page()
                    
                    # Set viewport size for better rendering
                    page.set_viewport_size({"width": 1280, "height": 720})
                    
                    # Add small delay for stability
                    page.set_default_timeout(15000)  # 15 seconds timeout
                    
                    data = crawl_city_data(page, city)
                    if data:  # Only process valid data
                        results.append(data)
                        # Save to CSV
                        csv_file = save_to_csv(data, city['name'])
                        print(f"Data saved to: {csv_file}")
                    else:
                        print(f"Skipping invalid data for {city['display_name']}")
                
                except Exception as e:
                    print(f"Browser error for {city['display_name']}: {str(e)}")
                    continue
                
                finally:
                    if 'browser' in locals():
                        browser.close()
        
        except Exception as e:
            print(f"Playwright error for {city['display_name']}: {str(e)}")
            continue
            
    return results

if __name__ == "__main__":
    try:
        print("Starting IQAir data crawler...")
        print(f"Current time in Vietnam: {get_vietnam_time().strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        results = crawl_all_cities()
        
        print("\nCrawled data:")
        print(json.dumps(results, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        raise e
