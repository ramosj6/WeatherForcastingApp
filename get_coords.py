import requests

def get_latitude_longitude_from_zip(zip_code, api_key):
    base_url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "address": zip_code,
        "key": api_key
    }

    response = requests.get(base_url, params=params)
    if response.status_code == 200:
        data = response.json()
        results = data.get("results", [])
        if results:
            location = results[0]["geometry"]["location"]
            latitude = location["lat"]
            longitude = location["lng"]
            #print("Latitude:", latitude)
            #print("Longitude:", longitude)
   
            formatted_address = results[0]["formatted_address"]
            locality = None
            administrative_area = None
            #print(results)
            # Extract locality and administrative area if available
            for component in results[0]["address_components"]:
                if "locality" in component["types"]:
                    locality = component["long_name"]
                elif "administrative_area_level_1" in component["types"]:
                    administrative_area = component["long_name"]
            
            return str(latitude), str(longitude), formatted_address, locality, administrative_area
        else:
            print("No results found for the provided zip code.")
            return None, None, None, None, None
    else:
        print(f"Geocoding API request failed with status code: {response.status_code}")
        return None, None, None, None, None
