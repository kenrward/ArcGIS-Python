AGS_AllFunctionsSecure.py
=============

This script updates the ArcGIS Server Administration Toolkit - 10.1+.
http://www.arcgis.com/home/item.html?id=12dde73e0e784e47818162b4d41ee340

1. Updated for Python 3.x
2. Secure passwords with getpass and use HTTPS for admin calls
3. Replace urllib with requests (http://docs.python-requests.org/en/latest/)

** NOTE **
-------------
You will get an HTTPS Warning since if your AGS servers are using self-signed certificates for HTTPS
