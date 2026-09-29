from countryinfo import CountryInfo
import pycountry
import requests

country_name = "bangladesh"
country_code = "bd"  # ISO alpha-2 code
country = CountryInfo(country_name)

# --- Basic country info ---
print("=== BASIC INFO ===")
print(f"Country: {country_name}")
print(f"Capital: {country.capital()}")
print(f"Population: {country.population()}")
print(f"Area: {country.area()} km²")
print(f"Currencies: {country.currencies()}")
print(f"Languages: {country.languages()}")
print(f"Borders: {country.borders()}")
print(f"Region: {country.region()}")
print(f"Subregion: {country.subregion()}")

# --- States/Provinces ---
print("\n=== STATES/PROVINCES ===")
subdivisions = list(pycountry.subdivisions.get(country_code=country_code))
print(f"Total states/provinces: {len(subdivisions)}")
for sub in subdivisions:
    print(f"- {sub.name} ({sub.type})")

# --- Extra facts from REST Countries API ---
print("\n=== EXTRA FACTS (REST Countries) ===")
resp = requests.get(f"https://restcountries.com/v3.1/alpha/{country_code}").json()
print(f"Flag: {resp.get('flag')}")
print(f"Timezones: {resp.get('timezones')}")
print(f"Driving side: {resp.get('car', {}).get('side')}")
print(f"Calling code: {resp.get('idd', {}).get('root', '')}{resp.get('idd', {}).get('suffixes', [''])[0]}")
print(f"UN member: {resp.get('unMember')}")

# --- Economic & social data from World Bank ---
def get_worldbank_data(code, indicator, label):
    url = f"https://api.worldbank.org/v2/country/{code}/indicator/{indicator}?format=json&mrnev=1"
    data = requests.get(url).json()
    try:
        value, year = data[1][0]['value'], data[1][0]['date']
        print(f"{label} ({year}): {value}")
    except (IndexError, KeyError, TypeError):
        print(f"{label}: Data not available")

print("\n=== ECONOMIC INFO (World Bank) ===")
get_worldbank_data(country_code, "NY.GDP.MKTP.CD", "GDP (current US$)")
get_worldbank_data(country_code, "NY.GDP.MKTP.KD.ZG", "GDP Growth (%)")
get_worldbank_data(country_code, "SL.UEM.TOTL.ZS", "Unemployment Rate (%)")
get_worldbank_data(country_code, "FP.CPI.TOTL.ZG", "Inflation Rate (%)")
get_worldbank_data(country_code, "NY.GDP.PCAP.CD", "GDP per Capita (US$)")

print("\n=== SOCIAL & ENVIRONMENT (World Bank) ===")
get_worldbank_data(country_code, "SP.DYN.LE00.IN", "Life Expectancy (years)")
get_worldbank_data(country_code, "SE.ADT.LITR.ZS", "Literacy Rate (%)")
get_worldbank_data(country_code, "IT.NET.USER.ZS", "Internet Users (% of population)")
get_worldbank_data(country_code, "EN.ATM.CO2E.PC", "CO2 Emissions per Capita (metric tons)")

# --- Live exchange rate ---
print("\n=== CURRENCY EXCHANGE RATE ===")
currency_code = list(country.currencies())[0] if country.currencies() else None
if currency_code:
    fx = requests.get(f"https://api.exchangerate-api.com/v4/latest/USD").json()
    rate = fx.get('rates', {}).get(currency_code)
    print(f"1 USD = {rate} {currency_code}" if rate else "Rate not found")