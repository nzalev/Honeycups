### Summary
Listens for probing on UDP 631 (CUPS OpenPrinting Vulnerabilities) and logs the IP and datagram data.


### Requirements
- Python 3.9+
- User: honeycups
- Logging directory: /home/honeycups

### Notes
- After binding on 631, it will change itself to the honeycups user
- It listens on 0.0.0.0