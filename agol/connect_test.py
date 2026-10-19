from getpass import getpass
from arcgis.gis import GIS

username = input("ArcGIS Online username: ")
gis = GIS("https://www.arcgis.com", username, getpass("Password: "))

me = gis.users.me
print("Signed in as:", me.username)
print("Role:", me.role, "| User type:", me.userLicenseTypeId)
print("Organization:", gis.properties.name)
print("arcgis version:", __import__("arcgis").__version__)
