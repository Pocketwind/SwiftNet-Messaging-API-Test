settings 파일 위치: ./settings.json<br><br>
settings = <br>
{<br>
	"consumerKey": "",<br>
	"consumerSecret": "",<br>
	"audience": "",<br>
	"subject": "",<br>
	"expirationTime": 900,<br>
	"url": "",<br>
	"revokeUrl": "",<br>
	"reportUrl":"",<br>
	"messageUrl":"",<br>
	"interActReportUrl":"",<br>
	"interActMessageUrl":"",<br>
	"ackUrl":"",<br>
	"fileActUrl":"",<br>
	"fileActAckUrl":"",<br>
	"fileActReportUrl":"",<br>
	"distUrl":"",<br>
	"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",<br>
	"scope": "",<br>
	"certificatePath": "",<br>
	"privatePath": "",<br>
	"useHSM": false,<br>
	"hsmID":"",<br>
	"hsmSecret":"",<br>
	"encryptionKey": "",<br>
	"proxies": {<br>
		"http": "",<br>
		"https": ""<br>
	},<br>
    "issuer": "",<br>
    "inputPath": "C:/AFT/in",<br>
    "outputPath": "C:/AFT/out",<br>
	"fileActInputPath": "C:/AFT/filein",<br>
	"fileActOutputPath": "C:/AFT/fileout",<br>
    "ackPath": "C:/AFT/ack",<br>
	"downloadPath": "C:/AFT/download",<br>
    "distFile": "distList.json",<br>
    "retrieveInterval": 5,<br>
    "downloadInterval": 5,<br>
	"maxDistSize": 200,<br>
	"singleSendService":true,<br>
	"fileActService":true,<br>
	"distService":true,<br>
	"downloadService":true,<br>
	"messageMakerService":false,<br>
	"socketListenerService": true,<br>
	"socketListenerHost": "0.0.0.0",<br>
	"socketListenerPort": 12345,<br>
	"socketBufferSize": 4096,<br>
	"socketEncoding": "utf-8",<br>
	"hmacSecret":"",<br>
	"magicByte":"0xEE",<br>
	"sslCertFile":"",<br>
	"sslKeyFile":""<br>
} <br>
