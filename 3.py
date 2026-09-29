from countryinfo import CountryInfo

# Specify the country
country_name = "russia"
country = CountryInfo(country_name)

# Fetch and display country information
print(f"Country: {country_name}")
print(f"Capital: {country.capital()}")
print(f"Population: {country.population()}")
print(f"Area: {country.area()} km²")
print(f"Currencies: {country.currencies()}")
print(f"Languages: {country.languages()}")
print(f"Borders: {country.borders()}")
print(f"Region: {country.region()}")
print(f"Subregion: {country.subregion()}")