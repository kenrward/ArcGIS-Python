import json, getpass, datetime, sys, requests, time
from collections import OrderedDict

'''
This script extends Esri's \ServerAdminToolkit scripts to do the following:
1) Updated for Python 3.x
2) Secure passwords with getpass and use HTTPS for admin calls
3) Replace urllib with requests (http://docs.python-requests.org/en/latest/)

** NOTE **
You will get an HTTPS Warning since if your AGS servers are using self-signed certificates for HTTPS
'''    
server =  input("Server ")
port = "6080"
sslport = "6443"
mapbaseUrl = "http://{}:{}/arcgis/rest/services/".format(server, port)
secbaseUrl = "https://{}:{}/arcgis/admin".format(server, sslport)
baseUrl = "http://{}:{}/arcgis/admin/services".format(server, port)

token =  None
menu = {1:"View ALL Services",2:"START ALL Services",3:"STOP ALL Services", 4:"Server Report", 10:"Exit"}


def printLines():
    ''' Simple funtion to print lines in menu '''
    print("\n*-----------------------------------------------*\n")
    
def checkToken(token):
    '''
    This function will ensure the token is not blanks
    TODO: Check to see if token is still valid (not expired)
    '''
    if token is None:    
        username = 'ken.ward' #input('Username ')
        password = getpass.getpass('Password ')
        token = gentoken(secbaseUrl+ '/generateToken', username, password)
    
def gentoken(url, username, password, expiration=60):
    '''
    Generates a token to pass to the rest of the functions.  This was modified to pass username/pass over
    HTTPS adding another layer of security.
    '''
    tokenpayload = {'username':   username,
                  'password':   password,
                  'expiration': str(expiration),
                  'client':     'requestip',
                  'f': 'json'}
    r = (requests.post(url, params=tokenpayload, verify=False))
    return r.json()['token']
    
def stopStartServices(stopStart, serviceList, token=None): 
    ''' 
    Function to stop, start or delete a service.
    Requires valid token
    stopStart = Stop|Start|Delete
    serviceList = List of services. A service must be in the <name>.<type> notation  
    '''       
    checkToken(token)
    
    if serviceList == "all":
        # grab a fresh catalog of services if "ALL"
        serviceList = getCatalog(token)
    else: 
        serviceList = [serviceList]

    
    for service in serviceList:
        op_service_url = secbaseUrl + '/services/' + service['folderName'] + '/' + service['serviceName'] +"."+ service['type'] + "/" + stopStart
        payload = {'f': 'json', 'token':   token}

        #Only HTTPS POST method i supported on the operation.
        r = (requests.post(op_service_url, params=payload, verify=False))
        status = r.json()
        
        if status['status'] == "success":
            print(stopStart + " successfully performed on " + service['serviceName'])
        else: 
            print("Failed to perform operation. Returned message from the server:")
            print(r.raise_for_status())
            print(status)
            print(op_service_url)
        
         
    
    return 
       
    

def getServerInfo(token=None):
    ''' Function to get and display a detailed report about a server
    Requires token
    service = String of existing service with type seperated by a period <serviceName>.<serviceType>
    '''    
    
    checkToken(token)    
     
    report = ''

    printLines()
    
    # Get Cluster and Machine info
    payload = {'f': 'json', 'token':   token}
    r1 = requests.post(secbaseUrl+"/clusters", params=payload, verify=False)
    jCluster = r1.json()
    if len(jCluster["clusters"]) == 0:        
        report += "No clusters found\n\n"
    else:    
        for cluster in jCluster["clusters"]:    
            report += "Cluster: {} is {}\n".format(cluster["clusterName"], cluster["configuredState"])            
            if len(cluster["machineNames"])     == 0:
                report += "    No machines associated with cluster\n"                
            else:
                # Get individual Machine info
                for machine in cluster["machineNames"]:                    
                    r2 = requests.post(secbaseUrl + "/machines/" + machine, params=payload, verify=False)
                    jMachine = r2.json()
                    report += "    Machine: {} is {}. (Platform: {})\n".format(machine, jMachine["configuredState"],jMachine["platform"])                    
        
                    
    # Get Version and Build
    r3 = requests.post(secbaseUrl + "/info", params=payload, verify=False)
    jInfo = r3.json()
    report += "\nVersion: {}\nBuild:   {}\n\n".format(jInfo["currentversion"], jInfo["currentbuild"])
      

    # Get Log level
    r4 = requests.post(secbaseUrl+"/logs/settings", params=payload, verify=False)
    jLog = r4.json()
    report += "Log level: {}\n\n".format(jLog["settings"]["logLevel"])
     
    
    #Get License information
    r5 = requests.post(secbaseUrl+"/system/licenses", params=payload, verify=False)
    jLicense = r5.json()
    report += "License is: {} / {}\n".format(jLicense["edition"]["name"], jLicense["level"]["name"])    
    if jLicense["edition"]["canExpire"] == True:
        import datetime
        d = datetime.date.fromtimestamp(jLicense["edition"]["expiration"] // 1000) #time in milliseconds since epoch
        report += "License set to expire: {}\n".format(datetime.datetime.strftime(d, '%Y-%m-%d'))        
    else:
        report += "License does not expire\n"        
    
        
    if len(jLicense["extensions"]) == 0:
        report += "No available extensions\n"        
    else:
        report += "Available Extenstions........\n"   
        for name in jLicense["extensions"]:            
            report += "extension:  {}\n".format(name["name"])            
               
    
    printLines()
    print(report)
    return
    
def getStatus(url,token=None):
    '''
    function to check if a serivce is running or not. 
    TODO: modify to take serviceList instead of a single service URL
    '''
    checkToken(token)
    payload = {'f': 'json', 'token':   token}
    r = (requests.get(url, params=payload, verify=False))
    return r.json()['realTimeState']
    
def getCluster(url,token=None):
    checkToken(token)
    payload = {'f': 'json', 'token':   token}
    r = (requests.post(url, params=payload, verify=False))
    return r.json()['clusterName']
    

    
def getCatalog(token=None):
    checkToken(token)
    payload = {'f': 'json', 'token':   token}
    r = (requests.get(secbaseUrl+'/services', params=payload, verify=False))
    catalog = r.json()
    if "error" in catalog: return
    services = catalog['services']
    # Build up list of folders and remove the System and Utilities folder (we dont want anyone playing with them)
    folders = catalog['folders']
    folders.remove("Utilities")             
    folders.remove("System")
    for folderName in folders:
        cat_r = (requests.get(secbaseUrl+ "/services/" + folderName, params=payload, verify=False))
        catalog = cat_r.json()
        services += catalog['services']
            
    return services
 
def printMenu():
    OrderedDict(sorted(menu.items(), key=lambda t: t[0]))
    printLines()
    for entry in menu: 
        print(entry, menu[entry])
    
    printLines()
    inSelect=int(input("\nPlease Select:")) 
    return inSelect

  #------------------
  # MAIN()
  #------------------
if __name__ == "__main__": 

    if token is None:
        username = input('Username ')
        password = getpass.getpass('Password ')
        token = gentoken(secbaseUrl+ '/generateToken', username, password)

    services = getCatalog(token)

    while True: 
        selection = printMenu()
        
        if selection ==1: 
            #"View All Services"
            for service in services:
                servRow = "{} | {} | {}".format(service['serviceName'],service['type'],service['folderName'])
                print(servRow)
                
        elif selection == 2:
            #"START ALL Services"
            stopStartServices("Start", "all", token)
            
        elif selection == 3:
            #"STOP ALL Services"
            stopStartServices("Stop", "all", token)
            
        elif selection == 4:
            #"Server Report"
            getServerInfo(token)
            
        elif selection == 10: 
            #EXIT
            break
        else: 
            print("Unknown Option Selected!")


    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    