from playwright.sync_api import sync_playwright
import json
from datetime import datetime
import csv
import pathlib
from zoneinfo import ZoneInfo
from typing import Dict, Optional
import re

# Define cities data
CITIES = [
    # Northern Vietnam
    {
        "name": "hanoi",
        "display_name": "Hà Nội",
        "url": "https://www.iqair.com/vi/vietnam/hanoi/hanoi",
    },
    {
        "name": "hai-phong",
        "display_name": "Hải Phòng",
        "url": "https://www.iqair.com/vi/vietnam/thanh-pho-hai-phong/haiphong",
    },
    {
        "name": "bac-ninh",
        "display_name": "Bắc Ninh",
        "url": "https://www.iqair.com/vi/vietnam/tinh-bac-ninh/bac-ninh",
    },
    # Central Vietnam
    {
        "name": "vinh",
        "display_name": "Vinh",
        "url": "https://www.iqair.com/vi/vietnam/tinh-nghe-an/vinh",
    },
    {
        "name": "hue",
        "display_name": "Huế",
        "url": "https://www.iqair.com/vietnam/tinh-thua-thien-hue/hue",
    },
    {
        "name": "da-nang",
        "display_name": "Đà Nẵng",
        "url": "https://www.iqair.com/vi/vietnam/da-nang/da-nang",
    },
    {
        "name": "nha-trang",
        "display_name": "Nha Trang",
        "url": "https://www.iqair.com/vi/vietnam/khanh-hoa/nha-trang",
    },
    {
        "name": "da-lat",
        "display_name": "Đà Lạt",
        "url": "https://www.iqair.com/vi/vietnam/tinh-lam-dong/da-lat",
    },
    {
        "name": "phan-thiet",
        "display_name": "Phan Thiết",
        "url": "https://www.iqair.com/vi/vietnam/tinh-binh-thuan/phan-thiet",
    },
    # Southern Vietnam
    {
        "name": "ho-chi-minh-city",
        "display_name": "Hồ Chí Minh",
        "url": "https://www.iqair.com/vi/vietnam/ho-chi-minh-city/ho-chi-minh-city",
    },
    {
        "name": "vung-tau",
        "display_name": "Hồ Chí Minh",
        "url": "https://www.iqair.com/vi/vietnam/ho-chi-minh-city/ho-chi-minh-city",
    },
    {
        "name": "can-tho",
        "display_name": "Cần Thơ",
        "url": "https://www.iqair.com/vi/vietnam/thanh-pho-can-tho/can-tho",
    },
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
    if icon and isinstance(icon, str):
        # New format: /dl/assets/svg/weather/ic-weather-01n.svg
        # Old format: /dl/web/weather/...
        if icon.startswith('/dl/assets/svg/weather/') or icon.startswith('/dl/web/weather/'):
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
    """Crawl data for a specific city using updated IQAir website structure (2024+)

    Raises exception for transient errors (browser closed, timeout) to allow retry.
    Returns None for data validation failures (no retry needed).
    """
    print(f"\nAccessing {city['display_name']} ({city['url']})...")

    # Navigate to city page - use domcontentloaded for faster initial load
    page.goto(city['url'], wait_until='domcontentloaded', timeout=45000)

    # Wait for the main AQI box to appear (new structure uses aqi-box-shadow classes)
    page.wait_for_selector('[class*="aqi-box-shadow"]', timeout=30000)

    # Small delay to ensure content is fully rendered
    page.wait_for_timeout(2000)

    # Extract data from the main AQI box
    main_box = page.query_selector('[class*="aqi-box-shadow"]')
    if not main_box:
        print(f"Could not find AQI box for {city['display_name']}")
        return None

    box_text = main_box.text_content()

    # Extract AQI value (first number in the text, e.g., "187AQI⁺ Mỹ...")
    aqi_match = re.search(r'^(\d+)', box_text)
    aqi_raw = aqi_match.group(1) if aqi_match else None

    # Extract wind speed (e.g., "7.1 km/h")
    wind_match = re.search(r'(\d+\.?\d*)\s*km/h', box_text)
    wind_speed_raw = wind_match.group(0) if wind_match else None

    # Extract humidity (e.g., "95 %" or "95%")
    humidity_match = re.search(r'(\d{1,3})\s*%', box_text)
    humidity_raw = humidity_match.group(0).replace(' ', '') if humidity_match else None

    # Extract weather icon from img tag
    weather_icon_el = page.query_selector('img[src*="ic-weather-"]')
    weather_icon_raw = weather_icon_el.get_attribute('src') if weather_icon_el else None

    # Validate all fields
    aqi = validate_aqi(aqi_raw) if aqi_raw else None
    weather_icon = validate_weather_icon(weather_icon_raw)
    wind_speed = validate_wind_speed(wind_speed_raw) if wind_speed_raw else None
    humidity = validate_humidity(humidity_raw) if humidity_raw else None

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
    """Crawl data for all cities with retry logic"""
    import time as time_module
    results = []
    max_retries = 3

    for city in CITIES:
        print(f"\n{'='*50}")
        print(f"Processing {city['display_name']}...")
        success = False

        for attempt in range(max_retries):
            if success:
                break

            playwright = None
            browser = None
            try:
                # Manual lifecycle management for better control
                playwright = sync_playwright().start()
                browser = playwright.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
                )
                context = browser.new_context(
                    viewport={"width": 1280, "height": 720},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
                page = context.new_page()

                # Set timeout for page operations
                page.set_default_timeout(60000)  # 60 seconds timeout

                data = crawl_city_data(page, city)
                if data:  # Only process valid data
                    results.append(data)
                    # Save to CSV
                    csv_file = save_to_csv(data, city['name'])
                    print(f"Data saved to: {csv_file}")
                    success = True
                else:
                    print(f"Skipping invalid data for {city['display_name']}")
                    success = True  # Don't retry for invalid data

            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"Attempt {attempt + 1} failed: {str(e)}")
                    print(f"Retrying in 2 seconds...")
                    time_module.sleep(2)
                else:
                    print(f"Failed after {max_retries} attempts: {str(e)}")

            finally:
                # Clean up resources
                try:
                    if browser:
                        browser.close()
                    if playwright:
                        playwright.stop()
                except Exception:
                    pass

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
